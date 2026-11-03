#!/usr/bin/env bash
# Run the native openEMS Python controller/port/module tests that the Rust
# packages already support.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"

export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

cd "$REPO_ROOT/openEMS/python/Tests"

status=0
for module in test_Automesh test_openEMS; do
  "$PYTHON" -m unittest "$module" -v || status=1
done
exit "$status"
