#!/usr/bin/env bash
# Differential check for curve excitations (RM-144 / the cavity regression).
#
# `combinedtests/cavity` excites a PEC cavity through an `<Excitation>` whose
# primitive is a `Curve`. The native engine walks the curve with
# `Operator::FindPath` and excites every edge on the path; the Rust port does
# the same. A regression here is silent: the probe files exist but are all
# zero, and the testsuite check (which compares a spectrum against `max(val)`)
# still passes.
#
# This script materialises the unmodified testsuite case, runs both solvers
# with the exact end criteria and compares the three voltage probes.
#
# Usage: scripts/ci/run_curve_excitation_check_wsl.sh
#   NATIVE_OPENEMS   native solver (default: ~/opt/openEMS/bin/openEMS)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_OPENEMS="${NATIVE_OPENEMS:-$HOME/opt/openEMS/bin/openEMS}"
RUST_BIN="$REPO_ROOT/target/release/openems-cli"

export PATH="$HOME/.cargo/bin:$PATH"

if [ ! -x "$NATIVE_OPENEMS" ]; then
  echo "missing native solver: $NATIVE_OPENEMS" >&2
  exit 2
fi
if [ ! -x "$RUST_BIN" ]; then
  echo "missing Rust solver: $RUST_BIN (cargo build --release -p openems-cli)" >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/cases" "$WORK/native" "$WORK/rust"

cd "$REPO_ROOT" || exit 1
octave --no-gui --quiet --eval \
  "addpath('scripts/ci'); materialize_perf_cases('$WORK/cases', 'cavity');" >/dev/null 2>&1 || {
  echo "failed to materialise the cavity case" >&2
  exit 1
}
cp "$WORK/cases/cavity.xml" "$WORK/native/input.xml"
cp "$WORK/cases/cavity.xml" "$WORK/rust/input.xml"

echo "== native"
( cd "$WORK/native" && "$NATIVE_OPENEMS" input.xml --exact-endcriteria > log 2>&1 ) || {
  echo "native run failed" >&2
  tail -20 "$WORK/native/log" >&2
  exit 1
}
echo "== rust"
( cd "$WORK/rust" && "$RUST_BIN" input.xml --exact-endcriteria > log 2>&1 ) || {
  echo "Rust run failed" >&2
  tail -20 "$WORK/rust/log" >&2
  exit 1
}

python3 - "$WORK" <<'PY'
import math
import sys
from pathlib import Path

work = Path(sys.argv[1])


def series(path):
    values = []
    for line in path.read_text().splitlines():
        if line.startswith("%") or not line.strip():
            continue
        parts = line.split()
        values.append(float(parts[1]))
    return values


failures = []
for name in ("ut1x", "ut1y", "ut1z"):
    native = series(work / "native" / name)
    rust = series(work / "rust" / name)
    if len(native) != len(rust):
        failures.append(f"{name}: {len(native)} native rows, {len(rust)} Rust rows")
        continue
    native_peak = max(abs(value) for value in native)
    rust_peak = max(abs(value) for value in rust)
    if native_peak == 0.0:
        failures.append(f"{name}: the native trace is identically zero (bad probe)")
        continue
    if rust_peak == 0.0:
        failures.append(f"{name}: the Rust trace is identically zero")
        continue
    scale = max(native_peak, 1e-30)
    difference = max(abs(a - b) for a, b in zip(native, rust)) / scale
    peak_difference = abs(rust_peak - native_peak) / scale
    print(f"  {name}: native peak {native_peak:.6e}, Rust peak {rust_peak:.6e}, "
          f"peak rel. difference {peak_difference:.3e}, "
          f"max sample rel. difference {difference:.3e}")
    # The probes integrate the same edges, so the peaks agree to the accumulated
    # f64 round-off; the per-sample trace also carries the tiny phase drift of a
    # high-Q cavity over 20000 steps. Measured on 2026-10-27: peaks <= 4.8e-5,
    # samples <= 1.7e-4; the bound is 1e-3 (5.8x margin), recorded in
    # docs/migration/REFERENCE_TOLERANCES.md.
    if difference > 1e-3 or peak_difference > 1e-3:
        failures.append(
            f"{name}: peak {peak_difference:.3e}, samples {difference:.3e} (bound 1e-3)"
        )

if failures:
    print("curve excitation check: FAIL", file=sys.stderr)
    for failure in failures:
        print(f"  {failure}", file=sys.stderr)
    sys.exit(1)
print("curve excitation check: PASS")
PY
