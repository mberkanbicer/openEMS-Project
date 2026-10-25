#!/usr/bin/env bash
# Run the native Python tests that the Rust packages already support.
#
# Slice of RM-095: the unmodified HDF5/SAR reader modules, the grid API, the
# mesh smoothing module and the CSXCAD utilities are exercised against the Rust
# core. The remaining CSXCAD class surface (properties, primitives,
# ContinuousStructure, transforms) is tracked in RM-090.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"

export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

cd "$REPO_ROOT/openEMS/python/Tests"
"$PYTHON" -m unittest test_hdf5_utils test_sar_utils -v

cd "$REPO_ROOT/CSXCAD/python/tests"
"$PYTHON" -m unittest test_Utilities test_CSRectGrid test_SmoothMeshLines test_CSTransform test_CSXCAD test_CSPrimitives test_CSProperties test_XML_RoundTrip test_WrapperCache -v

echo "native python test slice passed"
