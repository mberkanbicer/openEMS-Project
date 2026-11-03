#!/usr/bin/env bash
# Native differential check for the standalone cylindrical coefficient models
# of E-007.
#
# The fixtures under tests/fixtures/multigrid are two independent cylindrical
# operators (an inner and an outer rho range). This script compares the native
# and Rust `--debug-operator` dumps node by node, which isolates the coefficient
# normalization problem from the multi-grid engine. The native-layout operator
# pair (base = full mesh, child = inner rho + every second alpha line) and the
# engine are constructed and tested in crates/openems-core/src/multigrid.rs.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/opt/openEMS/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
FIXTURES="$REPO_ROOT/crates/openems-core/tests/fixtures/multigrid"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for case in ${CASES:-base child}; do
  model="$FIXTURES/$case.xml"
  if [ ! -f "$model" ]; then
    echo "missing multi-grid fixture: $model" >&2
    exit 1
  fi
  mkdir -p "$WORK/$case/native" "$WORK/$case/rust"
  ( cd "$WORK/$case/native" && "$NATIVE_BIN" "$model" --no-simulation --debug-operator >log 2>&1 )
  ( cd "$WORK/$case/rust" && "$RUST_BIN" "$model" --no-simulation --debug-operator >log 2>&1 )
  if [ ! -f "$WORK/$case/native/operator_dump.vtr" ]; then
    echo "native $case operator dump missing" >&2
    tail -5 "$WORK/$case/native/log" >&2
    exit 1
  fi
  python3 "$SCRIPT_DIR/compare_operator_dump.py" \
    "$WORK/$case/native/operator_dump.vtr" "$WORK/$case/rust/operator_dump.vtk" 1.0e-6 \
    || { echo "multi-grid $case operator dump check: FAIL"; exit 1; }
  echo "multi-grid $case operator dump check: PASS"
done
