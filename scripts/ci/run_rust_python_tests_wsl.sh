#!/usr/bin/env bash
# Run the native openEMS Python tests that only need the pure-Python modules.
#
# The full native suite additionally needs the CSXCAD class surface; the
# modules below exercise the HDF5 reader and the SAR reader against the native
# dump layout and are a first, verifiable slice of RM-095.
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
status=$?
echo "native python tests exit: $status"
exit $status
