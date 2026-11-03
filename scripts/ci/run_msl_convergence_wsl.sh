#!/usr/bin/env bash
# MSL shunt-open-stub notch convergence (RM-179).
#
# Re-runs the pinned smoke model at three mesh resolutions and records the
# |S11| peak / |S21| dip. Writes
# docs/migration/reference-data/convergence/msl_notch.json.
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
"$PYTHON" scripts/ci/msl_convergence.py "$@"
