#!/usr/bin/env python3
"""Fail when changed Rust sources contain placeholder implementations.

The migration policy forbids `todo!`, `unimplemented!`, "placeholder"/"stub"
markers and similar unfinished code. Deliberate invariants may use
`unreachable!`; files with a reviewed, bounded exception are listed in
``scripts/ci/placeholder_allowlist.txt`` as ``path: reason``.

Usage:
    check_placeholders.py             # check all tracked Rust files
    check_placeholders.py --changed   # check files changed against HEAD
    check_placeholders.py --self-test # verify the checker itself
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ALLOWLIST = Path(__file__).with_name("placeholder_allowlist.txt")

# (label, substring) matched case-insensitively against every line.
FORBIDDEN = [
    ("todo! macro", "todo!("),
    ("unimplemented! macro", "unimplemented!("),
    ("placeholder marker", "placeholder"),
    ("stub marker", "stub implementation"),
    ("not-implemented marker", "not implemented yet"),
    ("not-implemented marker", "not yet implemented"),
    ("not-implemented panic", 'panic!("not implemented'),
]


def load_allowlist() -> dict[str, str]:
    if not ALLOWLIST.exists():
        return {}
    entries: dict[str, str] = {}
    for raw in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path, _, reason = line.partition(":")
        entries[path.strip().replace("\\", "/")] = reason.strip()
    return entries


def repository_roots() -> list[Path]:
    """The repository root plus every initialized submodule.

    The Rust sources live in their owning submodule repositories, so scanning
    only the root repository would check nothing at all.
    """
    roots = [Path(".")]
    configuration = subprocess.run(
        ["git", "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"],
        capture_output=True,
        text=True,
    )
    if configuration.returncode not in (0, 1):
        configuration.check_returncode()
    for line in configuration.stdout.splitlines():
        _, _, path = line.partition(" ")
        path = path.strip()
        if not path:
            continue
        candidate = Path(path)
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def tracked_rust_files() -> list[Path]:
    files: list[Path] = []
    for root in repository_roots():
        output = subprocess.run(
            ["git", "-C", str(root), "ls-files", "*.rs"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for line in output.splitlines():
            if not line:
                continue
            files.append(root / line if root != Path(".") else Path(line))
    return files


def changed_rust_files(base: str) -> list[Path]:
    output = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", base, "--", "*.rs"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(line) for line in output.splitlines() if line]


def scan(paths: list[Path], allowlist: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        key = str(path).replace("\\", "/")
        if key in allowlist:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            findings.append(f"{key}: cannot read: {error}")
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            for label, needle in FORBIDDEN:
                if needle in lowered:
                    findings.append(f"{key}:{number}: {label}: {line.strip()}")
    return findings


def self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        seeded = root / "seeded.rs"
        seeded.write_text("fn f() { todo!() }\n", encoding="utf-8")
        clean = root / "clean.rs"
        clean.write_text(
            "fn f(x: u8) -> u8 { match x { 0 => 1, _ => unreachable!() } }\n",
            encoding="utf-8",
        )
        findings = scan([seeded, clean], {})
        if not any("seeded.rs" in finding for finding in findings):
            print("self-test failed: seeded placeholder was not detected", file=sys.stderr)
            return 1
        if any("clean.rs" in finding for finding in findings):
            print("self-test failed: clean file was flagged", file=sys.stderr)
            return 1
        key = str(seeded).replace("\\", "/")
        allowed = scan([seeded], {key: "self-test"})
        if allowed:
            print("self-test failed: allowlist was ignored", file=sys.stderr)
            return 1
    print("placeholder checker self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed", action="store_true", help="only files changed against --base")
    parser.add_argument("--base", default="HEAD", help="git revision to diff against")
    parser.add_argument("--self-test", action="store_true", help="run the self-test")
    arguments = parser.parse_args()

    if arguments.self_test:
        return self_test()

    paths = changed_rust_files(arguments.base) if arguments.changed else tracked_rust_files()
    findings = scan(paths, load_allowlist())
    if findings:
        print(f"Forbidden placeholder markers found in {len(findings)} line(s):", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print(
            "\nRemove the placeholder or add a reviewed exception to "
            "scripts/ci/placeholder_allowlist.txt.",
            file=sys.stderr,
        )
        return 1
    print(f"placeholder check passed ({len(paths)} Rust files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
