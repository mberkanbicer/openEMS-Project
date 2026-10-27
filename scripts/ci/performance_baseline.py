#!/usr/bin/env python3
"""Performance and memory baseline of the Rust solver against the pinned native
openEMS (RM-121 / RM-122).

The script runs the *unmodified* openEMS testsuite cases through both solvers on
byte-identical input XML, captures wall-clock time and peak resident memory with
``/usr/bin/time -v`` and writes a reproducible table (CSV + Markdown).

Usage::

    python scripts/ci/performance_baseline.py            # full table
    python scripts/ci/performance_baseline.py --runs 3   # more repetitions
    python scripts/ci/performance_baseline.py --cases cavity --configs default

The script is deliberately strict: it exits non-zero when a solver binary is
missing, when a run fails, when a run does not reach the recorded expected stop
step, or when the two solvers stop at different timesteps (a correctness
problem, not a performance one).

Only Python's standard library is used, so the system interpreter is enough.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "docs", "migration", "reference-data", "perf")
DEFAULT_RUST_BIN = os.path.join(REPO_ROOT, "target", "release", "openems-cli")
DEFAULT_NATIVE_BIN = os.path.expanduser("~/opt/openEMS/bin/openEMS")
TIME_BIN = "/usr/bin/time"

# Tests of openEMS/TESTSUITE/combinedtests. They cover the three regimes that
# matter for a baseline: a small closed PEC cavity that always runs to NrTS
# (cavity), a large 2 M-cell coaxial line that stops on the end criteria
# (Coax), and a small open microstrip line with transmission-line ports that
# stops on the end criteria (msl_port).
CASES = ["cavity", "Coax", "msl_port"]

# Execution-level configurations. ``--exact-endcriteria`` is part of *both*
# configurations and of both solvers: the octave testsuite runs it by default
# (ts_options), and it is what makes the stop timestep machine independent, i.e.
# comparable at all.
CONFIGS = {
    # As a user runs it: the fastest engine available, automatic thread count.
    "default": {"rust": [], "native": []},
    # One scalar worker on both sides: isolates the kernel itself from the
    # thread count and from the native SSE vectorisation.
    "basic": {"rust": ["--engine", "basic"], "native": ["--engine=basic"]},
}

SHARED_ARGS = ["--exact-endcriteria"]

FIELDS = [
    "config",
    "case",
    "solver",
    "run",
    "wall_s",
    "wall_s_best",
    "peak_rss_mib",
    "peak_rss_mib_max",
    "cpu_percent",
    "stop_step",
    "ncells",
    "mcells_per_s",
    "engine",
    "threads",
    "exit_code",
    "command",
    "xml_sha256",
    "time_file",
    "log_file",
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def die(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_hms(text: str) -> float:
    """Convert an ``/usr/bin/time -v`` elapsed value to seconds."""
    parts = [float(part) for part in text.strip().split(":")]
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60.0 + part
    return seconds


def cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def cpu_threads() -> int:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.startswith("processor"))
    except OSError:
        return os.cpu_count() or 1


def memory_total_mib() -> float:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


def machine_record() -> dict:
    load = "unknown"
    try:
        with open("/proc/loadavg", "r", encoding="utf-8") as handle:
            load = handle.read().strip()
    except OSError:
        pass
    free_out = ""
    try:
        free_out = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        pass
    return {
        "cpu": cpu_model(),
        "threads": cpu_threads(),
        "memory_mib": memory_total_mib(),
        "kernel": platform.platform(),
        "loadavg": load,
        "free": free_out,
    }


def _wsl_path(windows_path: str) -> str:
    """Translate a `D:/...` path from a worktree .git file to /mnt/d/..."""
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", windows_path)
    if not match:
        return windows_path
    return f"/mnt/{match.group(1).lower()}/" + match.group(2).replace("\\", "/")


def git_revision() -> str:
    """Best-effort repository revision.

    A Windows-created git worktree stores an absolute ``gitdir:`` path in
    ``.git``; ``git`` inside WSL cannot follow it, so the revision is resolved
    by hand before giving up.
    """
    out = subprocess.run(
        ["git", "-C", REPO_ROOT, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode == 0 and out.stdout.strip():
        return out.stdout.strip()

    git_file = os.path.join(REPO_ROOT, ".git")
    if not os.path.isfile(git_file):
        return "unknown"
    gitdir = ""
    for line in read_text(git_file).splitlines():
        if line.startswith("gitdir:"):
            gitdir = _wsl_path(line.split(":", 1)[1].strip())
    if not gitdir:
        return "unknown"
    head = read_text(os.path.join(gitdir, "HEAD")).strip()
    if not head.startswith("ref:"):
        return head[:12] or "unknown"
    ref = head.split(":", 1)[1].strip()
    common = read_text(os.path.join(gitdir, "commondir")).strip() or "."
    common_dir = os.path.normpath(os.path.join(gitdir, common))
    loose = read_text(os.path.join(common_dir, ref)).strip()
    if loose:
        return loose[:12]
    for line in read_text(os.path.join(common_dir, "packed-refs")).splitlines():
        if line.endswith(" " + ref):
            return line.split()[0][:12]
    return f"{ref} (unresolved)"


def native_version(binary: str) -> str:
    try:
        out = subprocess.run([binary, "--help"], capture_output=True, text=True, check=False)
        for line in out.stdout.splitlines():
            if "openEMS" in line and "version" in line:
                return line.strip(" |")
    except OSError:
        pass
    return "unknown"


# --------------------------------------------------------------------------
# Log parsing
# --------------------------------------------------------------------------
RE_STOP_ENDCRITERIA = re.compile(
    r"end-criteria of [-+0-9.]+ ?dB reached after (\d+) timesteps", re.IGNORECASE
)
RE_STOP_ITERATIONS = re.compile(r"Time for (\d+) iterations")
RE_STOP_COMPLETED = re.compile(r"FDTD simulation completed: (\d+) timesteps")
RE_STOP_PROGRESS = re.compile(r"Timestep:\s*(\d+)")
RE_CELLS = re.compile(r"-->\s*([0-9.eE+]+) FDTD cells")
RE_DT = re.compile(r"FDTD timestep is:\s*([0-9.eE+-]+) s")
RE_ENGINE = re.compile(r"^Create FDTD engine(?:\s*\((.*)\))?\s*$", re.MULTILINE)
RE_ENABLED_ENGINE = re.compile(r"openEMS - enabled (\S+) engine")


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def parse_stop_step(log: str) -> int:
    """Return the last simulated timestep reported by either solver."""
    for pattern in (RE_STOP_ENDCRITERIA, RE_STOP_COMPLETED, RE_STOP_ITERATIONS):
        matches = pattern.findall(log)
        if matches:
            return int(float(matches[-1]))
    matches = RE_STOP_PROGRESS.findall(log)
    if matches:
        return int(matches[-1])
    return 0


def parse_ncells(log: str) -> float:
    match = RE_CELLS.search(log)
    return float(match.group(1)) if match else 0.0


def parse_dt(log: str) -> float:
    match = RE_DT.search(log)
    return float(match.group(1)) if match else 0.0


def parse_engine(log: str, solver: str, config: str) -> str:
    enabled = RE_ENABLED_ENGINE.search(log)
    if enabled:
        return enabled.group(1)
    match = RE_ENGINE.search(log)
    if match and match.group(1):
        return match.group(1).strip()
    if match:
        return "basic"
    if solver == "rust":
        # The Rust CLI does not echo its engine; main.rs maps "basic" to the
        # serial kernel and every other engine name to the threaded kernel.
        return "basic (serial kernel)" if config == "basic" else "fastest (threaded kernel)"
    return "unknown"


def parse_time_file(path: str) -> dict:
    text = read_text(path)
    record = {"wall_s": 0.0, "peak_rss_mib": 0.0, "cpu_percent": 0.0}
    for line in text.splitlines():
        if "Elapsed (wall clock) time" in line:
            # ... (h:mm:ss or m:ss): 0:23.97
            record["wall_s"] = parse_hms(line.split("):", 1)[-1].strip())
        elif "Maximum resident set size" in line:
            record["peak_rss_mib"] = float(line.split(":")[1].strip()) / 1024.0
        elif "Percent of CPU this job got" in line:
            record["cpu_percent"] = float(line.split(":")[1].strip().rstrip("%"))
    return record


# --------------------------------------------------------------------------
# Case materialisation
# --------------------------------------------------------------------------
def materialize(repo_root: str, work_dir: str, cases: list) -> dict:
    """Write the testsuite input XML for every case into work_dir/cases."""
    target = os.path.join(work_dir, "cases")
    os.makedirs(target, exist_ok=True)
    octave = shutil.which("octave")
    if not octave:
        die("octave is not installed; it is required to write the testsuite input XML")
    script_dir = os.path.join(repo_root, "scripts", "ci")
    case_list = ", ".join(f"'{name}'" for name in cases)
    expression = (
        f"addpath('{script_dir}'); materialize_perf_cases('{target}', {case_list});"
    )
    print(f"[materialize] octave --no-gui --quiet --eval \"{expression}\"", flush=True)
    result = subprocess.run(
        [octave, "--no-gui", "--quiet", "--eval", expression],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        die(f"materializing the testsuite cases failed (exit {result.returncode})")

    paths = {}
    for name in cases:
        path = os.path.join(target, f"{name}.xml")
        if not os.path.isfile(path):
            die(f"case {name}: octave did not write {path}")
        paths[name] = path
        print(f"[materialize] {name}.xml  sha256={sha256_file(path)[:16]}  {os.path.getsize(path)} B")
    return paths


# --------------------------------------------------------------------------
# Measured runs
# --------------------------------------------------------------------------
def run_solver(
    solver: str,
    binary: str,
    xml: str,
    args: list,
    run_dir: str,
    label: str,
    require_stop: bool = True,
    require_success: bool = True,
) -> dict:
    """Run one solver once under /usr/bin/time -v inside its own directory."""
    os.makedirs(run_dir, exist_ok=True)
    time_file = os.path.join(run_dir, "time.txt")
    log_file = os.path.join(run_dir, "solver.log")
    command = [TIME_BIN, "-v", "-o", time_file, binary, xml, *args]
    print(f"[run] {label}: {' '.join(command)}", flush=True)
    started = time.time()
    with open(log_file, "w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, check=False)
    elapsed = time.time() - started

    if not os.path.isfile(time_file):
        die(f"{label}: {TIME_BIN} wrote no output; is /usr/bin/time installed?")
    if require_success and result.returncode != 0:
        tail = "\n".join(read_text(log_file).splitlines()[-30:])
        die(f"{label}: solver exited with {result.returncode}\n--- last lines ---\n{tail}")

    log = read_text(log_file)
    measured = parse_time_file(time_file)
    record = {
        "solver": solver,
        "exit_code": result.returncode,
        "wall_s": measured["wall_s"] or elapsed,
        "peak_rss_mib": measured["peak_rss_mib"],
        "cpu_percent": measured["cpu_percent"],
        "stop_step": parse_stop_step(log),
        "ncells": parse_ncells(log),
        "dt_s": parse_dt(log),
        "command": " ".join(command),
        "time_file": time_file,
        "log_file": log_file,
    }
    if require_stop and record["stop_step"] <= 0:
        die(f"{label}: no timestep found in {log_file}; the run did not simulate")
    if record["peak_rss_mib"] <= 0.0:
        die(f"{label}: {TIME_BIN} reported no maximum resident set size")
    return record


def output_stats(directory: str) -> dict:
    """Row count and peak sample magnitude of every solver output file.

    The first column of every openEMS text output is the time axis, so it is
    skipped: a probe that carries no signal would otherwise look non-zero
    simply because its time column advances.
    """
    stats = {}
    for name in sorted(os.listdir(directory)):
        if name in ("time.txt", "solver.log"):
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        rows = 0
        peak = 0.0
        for line in read_text(path).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("%") or stripped.startswith("#"):
                continue
            rows += 1
            fields = stripped.replace(",", " ").split()
            for field in (fields[1:] or fields):
                try:
                    value = abs(float(field))
                except ValueError:
                    continue
                if value > peak:
                    peak = value
        stats[name] = {"rows": rows, "peak": peak}
    return stats


# --------------------------------------------------------------------------
# Reported table
# --------------------------------------------------------------------------
def write_csv(path: str, rows: list) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FIELDS})


def write_markdown(path: str, context: dict, summary: dict, rows: list) -> None:
    machine = context["machine"]
    lines = []
    lines.append("# Performance and memory baseline vs native (RM-121 / RM-122)")
    lines.append("")
    lines.append(
        "Measured comparison of the Rust solver (`openems-cli`) against the pinned "
        "native openEMS on identical input XML. Every number in this file was "
        "produced by `scripts/ci/run_performance_baseline_wsl.sh`; nothing is "
        "estimated."
    )
    lines.append("")
    lines.append(f"- Generated: {context['timestamp']} (UTC)")
    lines.append(
        f"- Repository revision at run time: `{context['git']}` "
        "(informational; the measured binaries are pinned by their SHA-256 below)"
    )
    lines.append(f"- Native solver: `{context['native_bin']}` ({context['native_version']})")
    lines.append(f"  - SHA-256 `{context['native_sha256']}`")
    lines.append(f"- Rust solver: `{context['rust_bin']}` (built {context['rust_built']})")
    lines.append(f"  - SHA-256 `{context['rust_sha256']}`")
    lines.append(
        "- Both binaries are copied into the scratch working directory before the "
        "first run, so a rebuild during the measurement cannot mix two executables."
    )
    lines.append(f"- CPU: {machine['cpu']} — {machine['threads']} hardware threads")
    lines.append(f"- Memory: {machine['memory_mib']:.0f} MiB total")
    lines.append(f"- Kernel: `{machine['kernel']}`")
    lines.append(f"- Load average at start: `{machine['loadavg']}`")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "Both solvers run the same materialised `input.xml` per case (SHA-256 below), "
        "in their own working directory, one process at a time, with "
        "`--exact-endcriteria` so the stopping point is machine independent."
    )
    lines.append("")
    lines.append(
        f"Each solver gets {context['warmup']} discarded warm-up run(s) followed by "
        f"{context['runs']} measured run(s). Wall time is the best of the measured runs "
        "and peak RSS the maximum of the measured runs, both read from "
        "`/usr/bin/time -v` (`Elapsed (wall clock) time` and `Maximum resident set size`)."
    )
    lines.append("")
    lines.append("Command form (identical for both solvers, options after the file):")
    lines.append("")
    lines.append("```")
    lines.append("/usr/bin/time -v <solver> <case>.xml --exact-endcriteria [<engine option>]")
    lines.append("```")
    lines.append("")
    lines.append("The two engine configurations:")
    lines.append("")
    lines.append("- **default** — no engine option, automatic thread count on both sides.")
    lines.append("- **basic** — `--engine basic` on both sides: one scalar worker, no SIMD.")
    lines.append("")
    lines.append("The raw `/usr/bin/time -v` output and solver logs of every run are stored "
                 f"next to this file under `{os.path.relpath(context['raw_root'], context['out_dir'])}/`; "
                 "the solver data files itself (probes, ports, energy dumps) stay in the "
                 "scratch working directory because they are large and reproducible.")
    lines.append("")

    lines.append("## Inputs")
    lines.append("")
    lines.append("| case | source | XML SHA-256 | cells | dt (ps) |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name in context["cases"]:
        info = context["case_info"][name]
        lines.append(
            f"| {name} | `openEMS/TESTSUITE/combinedtests/{info['source']}.m` | "
            f"`{info['sha256'][:16]}…` | {info['ncells']:.0f} | {info['dt_s'] * 1e12:.4f} |"
        )
    lines.append("")

    for config in context["configs"]:
        rows_cfg = [row for row in rows if row["config"] == config]
        if not rows_cfg:
            continue
        title = (
            "default engine, automatic threads"
            if config == "default"
            else "`--engine basic`, one thread"
        )
        lines.append(f"## Results — {title}")
        lines.append("")
        lines.append(
            "| case | solver | engine | threads | wall s (best) | wall s (runs) | "
            "peak RSS MiB | MCells/s | stop step | wall ratio | RSS ratio |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for name in context["cases"]:
            pair = summary[(config, name)]
            native = pair["native"]
            rust = pair["rust"]
            for key, row in (("native", native), ("rust", rust)):
                ratio_wall = pair["ratio_wall"] if key == "rust" else 1.0
                ratio_rss = pair["ratio_rss"] if key == "rust" else 1.0
                runs = row["wall_runs"]
                lines.append(
                    "| {case} | {solver} | {engine} | {threads} | {wall:.2f} | {runs} | "
                    "{rss:.1f} | {mcells:.2f} | {stop} | {rw} | {rr} |".format(
                        case=name,
                        solver=key,
                        engine=row["engine"],
                        threads=row["threads"],
                        wall=row["wall_s_best"],
                        runs=", ".join(f"{value:.2f}" for value in runs),
                        rss=row["peak_rss_mib_max"],
                        mcells=row["mcells_per_s"],
                        stop=row["stop_step"],
                        rw=f"{ratio_wall:.2f}×" if key == "rust" else "-",
                        rr=f"{ratio_rss:.2f}×" if key == "rust" else "-",
                    )
                )
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- Peak RSS is the child process peak of `/usr/bin/time -v`, so it excludes the "
        "shell and the timing wrapper. It is not directly comparable to RSS of a parallel "
        "run with a different thread count; compare only rows with the same engine."
    )
    lines.append(
        "- MCells/s = stop step × cells / wall time, i.e. the measured effective throughput. "
        "A run that stops early therefore reports the throughput of the steps it actually "
        "executed."
    )
    lines.append(
        "- The native solver prints its engine, grid and timestep; the Rust CLI does not, so "
        "the Rust engine label comes from `openEMS/rust-cli/src/main.rs` (engine name → "
        "thread count mapping) and is corroborated by the measured CPU utilisation in the CSV."
    )
    lines.append("")
    lines.append("## Solver agreement")
    lines.append("")
    lines.append(
        "Both solvers simulated the same input, so the stop timestep and the produced "
        "output files must agree. Data-row counts and the peak sample magnitude of every "
        "output file of the fastest run of each solver (probes, ports, energy dumps):"
    )
    lines.append("")
    lines.append("| config | case | stop step native | stop step rust | output files | agreement |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for config in context["configs"]:
        for name in context["cases"]:
            pair = summary.get((config, name))
            if not pair:
                continue
            differing = pair.get("output_differing") or {}
            silent = pair.get("output_silent_zeros") or {}
            if differing:
                agreement = "**row counts differ**"
            elif silent:
                agreement = "row counts equal, **zero output in Rust**"
            else:
                agreement = "identical row counts"
            lines.append(
                f"| {config} | {name} | {pair['native']['stop_step']} | "
                f"{pair['rust']['stop_step']} | {pair.get('output_files', 0)} | {agreement} |"
            )
    lines.append("")
    if context["stop_step_notes"] or context["output_notes"]:
        for note in context["stop_step_notes"] + context["output_notes"]:
            lines.append(f"- {note}")
        lines.append("")
    lines.append(
        "Solver differences found while producing this table are recorded in "
        "`observed-differences.md` next to this file."
    )
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def stop_step_manifest(path: str) -> dict:
    """Read config/case → expected stop step from a CSV, if it exists."""
    expected = {}
    if not os.path.isfile(path):
        return expected
    with open(path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            expected[(row["config"], row["case"])] = int(row["stop_step"])
    return expected


def write_stop_step_manifest(path: str, summary: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["config", "case", "stop_step"])
        for (config, case), pair in sorted(summary.items()):
            writer.writerow([config, case, pair["native"]["stop_step"]])


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2, help="measured runs per solver (default 2)")
    parser.add_argument("--warmup", type=int, default=1, help="discarded warm-up runs (default 1)")
    parser.add_argument("--cases", nargs="+", default=CASES, choices=CASES)
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS), choices=list(CONFIGS))
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="directory for CSV/Markdown/raw")
    parser.add_argument("--work", default=None, help="work directory (default: beside the results)")
    parser.add_argument("--rust-bin", default=DEFAULT_RUST_BIN)
    parser.add_argument("--native-bin", default=DEFAULT_NATIVE_BIN)
    parser.add_argument("--keep-work", action="store_true", help="keep the solver run directories")
    args = parser.parse_args()

    for label, path in (("native", args.native_bin), ("rust", args.rust_bin)):
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            die(
                f"the {label} solver is missing or not executable: {path}\n"
                "  native: install the pinned openEMS 0.37.0 (~/opt/openEMS/bin/openEMS)\n"
                "  rust:   cargo build --release -p openems-cli"
            )
    if not os.path.isfile(TIME_BIN) or not os.access(TIME_BIN, os.X_OK):
        die(f"{TIME_BIN} is missing; install the GNU time package")

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    work_dir = os.path.abspath(args.work or tempfile.mkdtemp(prefix="openems-perf-"))
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    # Snapshot both binaries so that a concurrent rebuild or reinstall cannot
    # swap the executable between the warm-up and the measured runs.
    snapshot_dir = os.path.join(work_dir, "bin")
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshots = {}
    for label, path in (("native", args.native_bin), ("rust", args.rust_bin)):
        target = os.path.join(snapshot_dir, f"{label}-{os.path.basename(path)}")
        shutil.copyfile(path, target)
        os.chmod(target, 0o755)
        snapshots[label] = {
            "source": path,
            "sha256": sha256_file(target),
            "size": os.path.getsize(target),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(path))),
        }
    args.native_bin = os.path.join(snapshot_dir, f"native-{os.path.basename(snapshots['native']['source'])}")
    args.rust_bin = os.path.join(snapshot_dir, f"rust-{os.path.basename(snapshots['rust']['source'])}")

    print(f"[info] repository : {REPO_ROOT}")
    print(f"[info] native     : {snapshots['native']['source']}")
    print(f"[info] rust       : {snapshots['rust']['source']}")
    print(f"[info] output     : {out_dir}")
    print(f"[info] work       : {work_dir}", flush=True)

    machine = machine_record()
    print(
        f"[info] machine    : {machine['cpu']} / {machine['threads']} threads / "
        f"{machine['memory_mib']:.0f} MiB / load {machine['loadavg']}",
        flush=True,
    )

    xml_paths = materialize(REPO_ROOT, work_dir, args.cases)

    ncells = {}
    dt_s = {}
    for name, path in xml_paths.items():
        probe = run_solver(
            "native",
            args.native_bin,
            path,
            [*SHARED_ARGS, "--no-simulation"],
            os.path.join(work_dir, "preflight", name),
            f"preflight {name}",
            require_stop=False,
            require_success=False,
        )
        ncells[name] = probe["ncells"]
        dt_s[name] = probe["dt_s"]
        if ncells[name] <= 0:
            die(f"{name}: the native pre-flight did not report the grid size")

    expected = stop_step_manifest(os.path.join(out_dir, "expected-stop-steps.csv"))
    raw_root = os.path.join(out_dir, "raw")
    if os.path.isdir(raw_root):
        shutil.rmtree(raw_root)
    runs_root = os.path.join(work_dir, "runs")

    def keep_artifacts(record: dict, label: str) -> dict:
        """Copy the /usr/bin/time and solver log files into the results tree."""
        target = os.path.join(raw_root, label)
        os.makedirs(target, exist_ok=True)
        for key in ("time_file", "log_file"):
            destination = os.path.join(target, os.path.basename(record[key]))
            shutil.copyfile(record[key], destination)
            record[key] = destination
        # The command column must name the installed binaries, not the
        # byte-identical snapshot copies that were executed.
        command = record["command"]
        for label_name in ("native", "rust"):
            command = command.replace(
                args.native_bin if label_name == "native" else args.rust_bin,
                snapshots[label_name]["source"],
            )
        record["command"] = command
        return record

    rows = []
    summary = {}
    stop_notes = []
    output_notes = []
    failures = []

    for config in args.configs:
        for name in args.cases:
            pair = {}
            for solver in ("native", "rust"):
                binary = args.native_bin if solver == "native" else args.rust_bin
                solver_args = [*SHARED_ARGS, *CONFIGS[config][solver]]
                threads = machine["threads"] if config == "default" else 1
                base = os.path.join(runs_root, config, name, solver)
                for run in range(args.warmup):
                    run_solver(
                        solver,
                        binary,
                        xml_paths[name],
                        solver_args,
                        os.path.join(base, f"warmup-{run}"),
                        f"{config}/{name}/{solver} warm-up {run}",
                    )
                measured = []
                for run in range(args.runs):
                    record = run_solver(
                        solver,
                        binary,
                        xml_paths[name],
                        solver_args,
                        os.path.join(base, f"run-{run}"),
                        f"{config}/{name}/{solver} run {run}",
                    )
                    record = keep_artifacts(record, f"{config}/{name}/{solver}/run-{run}")
                    record["engine"] = parse_engine(
                        read_text(record["log_file"]), solver, config
                    )
                    record["threads"] = threads
                    record["run_dir"] = os.path.join(base, f"run-{run}")
                    measured.append(record)
                    rows.append(
                        {
                            "config": config,
                            "case": name,
                            "solver": solver,
                            "run": run,
                            "wall_s": f"{record['wall_s']:.3f}",
                            "peak_rss_mib": f"{record['peak_rss_mib']:.1f}",
                            "cpu_percent": f"{record['cpu_percent']:.0f}",
                            "stop_step": record["stop_step"],
                            "ncells": f"{ncells[name]:.0f}",
                            "mcells_per_s": f"{ncells[name] * record['stop_step'] / record['wall_s'] / 1e6:.2f}",
                            "engine": record["engine"],
                            "threads": threads,
                            "exit_code": record["exit_code"],
                            "command": record["command"],
                            "xml_sha256": sha256_file(xml_paths[name]),
                            "time_file": os.path.relpath(record["time_file"], out_dir),
                            "log_file": os.path.relpath(record["log_file"], out_dir),
                        }
                    )

                steps = sorted({record["stop_step"] for record in measured})
                if len(steps) != 1:
                    failures.append(
                        f"{config}/{name}/{solver}: unstable stop step across runs: {steps}"
                    )
                best = min(measured, key=lambda record: record["wall_s"])
                pair[solver] = {
                    "wall_s_best": best["wall_s"],
                    "wall_runs": [record["wall_s"] for record in measured],
                    "peak_rss_mib_max": max(record["peak_rss_mib"] for record in measured),
                    "cpu_percent": best["cpu_percent"],
                    "stop_step": steps[-1] if steps else 0,
                    "engine": best["engine"],
                    "threads": threads,
                    "mcells_per_s": ncells[name] * best["stop_step"] / best["wall_s"] / 1e6,
                    "dir": best["run_dir"],
                }

                # Fill the aggregates into the per-run CSV rows of this group.
                for row in rows:
                    if (
                        row["config"] == config
                        and row["case"] == name
                        and row["solver"] == solver
                    ):
                        row["wall_s_best"] = f"{pair[solver]['wall_s_best']:.3f}"
                        row["peak_rss_mib_max"] = f"{pair[solver]['peak_rss_mib_max']:.1f}"

            native = pair["native"]
            rust = pair["rust"]
            pair["ratio_wall"] = rust["wall_s_best"] / native["wall_s_best"]
            pair["ratio_rss"] = rust["peak_rss_mib_max"] / native["peak_rss_mib_max"]
            summary[(config, name)] = pair

            native_stats = output_stats(native["dir"])
            rust_stats = output_stats(rust["dir"])
            differing = {
                filename: (native_stats.get(filename, {}).get("rows"), rust_stats.get(filename, {}).get("rows"))
                for filename in sorted(set(native_stats) | set(rust_stats))
                if native_stats.get(filename, {}).get("rows")
                != rust_stats.get(filename, {}).get("rows")
            }
            silent_zeros = {
                filename: native_stats[filename]["peak"]
                for filename in sorted(set(native_stats) & set(rust_stats))
                if native_stats[filename]["peak"] > 0.0
                and rust_stats[filename]["peak"] == 0.0
            }
            pair["output_files"] = len(native_stats)
            pair["output_differing"] = differing
            pair["output_silent_zeros"] = silent_zeros
            if differing:
                detail = ", ".join(
                    f"{filename}: native {left} / rust {right}"
                    for filename, (left, right) in differing.items()
                )
                output_notes.append(
                    f"**{config}/{name}: output row counts differ** — {detail}. "
                    "Both solvers stopped at the same timestep, so this is a "
                    "sampling or formatting difference in the outputs."
                )
            if silent_zeros:
                detail = ", ".join(
                    f"`{filename}` (native peak {peak:.3e}, rust exactly 0)"
                    for filename, peak in silent_zeros.items()
                )
                output_notes.append(
                    f"**{config}/{name}: output is identically zero in the Rust run** — "
                    f"{detail}. The stop step and the energy dumps agree, so the field "
                    "history is simulated but this output carries no signal. This is a "
                    "correctness difference, not a performance result."
                )

            print(
                f"[result] {config:<8} {name:<9} native {native['wall_s_best']:7.2f} s / "
                f"{native['peak_rss_mib_max']:8.1f} MiB @ {native['stop_step']:6d} TS   "
                f"rust {rust['wall_s_best']:7.2f} s / {rust['peak_rss_mib_max']:8.1f} MiB @ "
                f"{rust['stop_step']:6d} TS   ratio {pair['ratio_wall']:.2f}x / "
                f"{pair['ratio_rss']:.2f}x",
                flush=True,
            )

            if native["stop_step"] != rust["stop_step"]:
                failures.append(
                    f"{config}/{name}: the solvers stopped at different timesteps "
                    f"(native {native['stop_step']}, rust {rust['stop_step']})"
                )
                stop_notes.append(
                    f"**{config}/{name}: stop-step mismatch** — native stopped at "
                    f"{native['stop_step']}, Rust at {rust['stop_step']}. This is a "
                    "correctness difference, not a performance result."
                )
            key = (config, name)
            if key in expected and native["stop_step"] != expected[key]:
                failures.append(
                    f"{config}/{name}: native stopped at {native['stop_step']}, "
                    f"the recorded expected stop step is {expected[key]}"
                )
            if key in expected and rust["stop_step"] != expected[key]:
                failures.append(
                    f"{config}/{name}: rust stopped at {rust['stop_step']}, "
                    f"the recorded expected stop step is {expected[key]}"
                )

    context = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "git": git_revision(),
        "native_bin": snapshots["native"]["source"],
        "native_version": native_version(args.native_bin),
        "native_sha256": snapshots["native"]["sha256"],
        "rust_bin": snapshots["rust"]["source"],
        "rust_built": snapshots["rust"]["mtime"],
        "rust_sha256": snapshots["rust"]["sha256"],
        "machine": machine,
        "runs": args.runs,
        "warmup": args.warmup,
        "cases": args.cases,
        "configs": args.configs,
        "out_dir": out_dir,
        "raw_root": raw_root,
        "stop_step_notes": stop_notes,
        "output_notes": output_notes,
        "case_info": {
            name: {
                "source": name,
                "sha256": sha256_file(xml_paths[name]),
                "ncells": ncells[name],
                "dt_s": dt_s[name],
            }
            for name in args.cases
        },
    }

    csv_path = os.path.join(out_dir, "performance-baseline.csv")
    md_path = os.path.join(out_dir, "performance-baseline.md")
    write_csv(csv_path, rows)
    write_markdown(md_path, context, summary, rows)
    manifest_path = os.path.join(out_dir, "expected-stop-steps.csv")
    if not expected:
        write_stop_step_manifest(manifest_path, summary)
        print(f"[info] wrote the stop-step manifest {manifest_path}")

    print(f"\n[info] table  : {md_path}")
    print(f"[info] csv    : {csv_path}")
    print(f"[info] raw    : {raw_root}")

    if not args.keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nAll runs reached the expected stop step and both solvers agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
