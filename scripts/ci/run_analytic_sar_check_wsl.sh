#!/usr/bin/env bash
# Analytic SAR validation (VAL-002): homogeneous lossy TEM line at 2 GHz.
#
# Runs the Rust engine through the Python bindings and compares the measured
# attenuation, phase constant and SAR slope with the exact lossy-medium
# solution. Writes docs/migration/reference-data/convergence/analytic_sar.json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_ROOT"
"$PYTHON" scripts/ci/analytic_sar_check.py "$@"
