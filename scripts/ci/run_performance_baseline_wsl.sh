#!/usr/bin/env bash
# RM-121 / RM-122: measured performance and peak-memory baseline of the Rust
# solver against the pinned native openEMS.
#
# Both solvers run the *unmodified* openEMS/TESTSUITE/combinedtests cases on
# byte-identical input XML; wall time and peak RSS come from /usr/bin/time -v.
# The results (CSV + Markdown table + the raw time/log files of every run) are
# written to docs/migration/reference-data/perf.
#
# Usage:
#   scripts/ci/run_performance_baseline_wsl.sh                 # full table
#   scripts/ci/run_performance_baseline_wsl.sh --runs 3        # more repetitions
#   scripts/ci/run_performance_baseline_wsl.sh --cases cavity --configs default
#
# Environment:
#   NATIVE_OPENEMS   native solver (default: ~/opt/openEMS/bin/openEMS)
#   RUST_BIN         Rust solver (default: <repo>/target/release/openems-cli)
#   PERF_SKIP_BUILD  set to 1 to reuse an existing release binary
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_OPENEMS="${NATIVE_OPENEMS:-$HOME/opt/openEMS/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"

export PATH="$HOME/.cargo/bin:$PATH"

if [ ! -x "$NATIVE_OPENEMS" ]; then
  echo "missing pinned native solver: $NATIVE_OPENEMS" >&2
  echo "set NATIVE_OPENEMS to the openEMS 0.37.0 binary" >&2
  exit 1
fi

if [ "${PERF_SKIP_BUILD:-0}" != "1" ]; then
  echo "== building the Rust CLI =="
  ( cd "$REPO_ROOT" && cargo build --release -p openems-cli )
fi

if [ ! -x "$RUST_BIN" ]; then
  echo "missing Rust solver: $RUST_BIN (cargo build --release -p openems-cli)" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/performance_baseline.py" \
  --rust-bin "$RUST_BIN" \
  --native-bin "$NATIVE_OPENEMS" \
  "$@"
