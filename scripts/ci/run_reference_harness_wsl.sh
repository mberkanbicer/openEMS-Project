#!/usr/bin/env bash
# Run the differential reference harness against the stored native captures.
#
# Usage: scripts/ci/run_reference_harness_wsl.sh [--case <name>] [--keep]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"

export PYTHONPATH="$REPO_ROOT/crates/openems-py/python:$REPO_ROOT/crates/csxcad-python/python${PYTHONPATH:+:$PYTHONPATH}"

PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

exec "$PYTHON" "$SCRIPT_DIR/reference_harness.py" "$@"
