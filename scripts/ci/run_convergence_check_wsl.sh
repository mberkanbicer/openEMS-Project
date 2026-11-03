#!/usr/bin/env bash
# Mesh-refinement study for the canonical PEC cavity (RM-170).
#
# Runs the Rust engine through the Python bindings at h, h/2 and h/4 and
# records the TE101 resonance, the relative error against the analytic mode and
# the observed order. Writes docs/migration/reference-data/convergence/cavity.json.
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
"$PYTHON" scripts/ci/convergence_study.py "$@"
