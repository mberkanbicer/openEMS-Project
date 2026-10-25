#!/usr/bin/env bash
# Run the native Python test suites against the Rust packages.
#
# Slice of RM-095: the unmodified CSXCAD and openEMS Python test modules run
# against the Rust core (CSXCAD geometry, openEMS controller, ports, NF2FF,
# SAR, HDF5 dumps).
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
"$PYTHON" -m unittest \
  test_hdf5_utils \
  test_sar_utils \
  test_sar_analytic \
  test_SAR_Calculation \
  test_Automesh \
  test_openEMS \
  test_Ports \
  test_XML_RoundTrip \
  test_nf2ff \
  test_sim_scripts

cd "$REPO_ROOT/CSXCAD/python/tests"
"$PYTHON" -m unittest \
  test_Utilities \
  test_CSRectGrid \
  test_SmoothMeshLines \
  test_CSTransform \
  test_CSXCAD \
  test_CSPrimitives \
  test_CSProperties \
  test_XML_RoundTrip \
  test_WrapperCache

echo "native python suites passed"
