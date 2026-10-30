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
# The carried upstream `test_openEMS` module also contains GPU-plugin tests.
# This build has no GPU engine (ADR 0002), so those tests are reported as
# SKIPPED rather than failed, faked or silently dropped.
"$PYTHON" - <<'PY'
import unittest
import test_openEMS


def split(suite):
    kept = unittest.TestSuite()
    skipped = 0
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            part, count = split(test)
            kept.addTest(part)
            skipped += count
        elif type(test).__name__ == "Test_GPUPlugins":
            skipped += 1
        else:
            kept.addTest(test)
    return kept, skipped


kept, skipped = split(unittest.TestLoader().loadTestsFromModule(test_openEMS))
print("SKIPPED: {} GPU plugin tests (no GPU engine in this build; ADR 0002)".format(skipped))
result = unittest.TextTestRunner(verbosity=1).run(kept)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY

"$PYTHON" -m unittest \
  test_hdf5_utils \
  test_sar_utils \
  test_sar_analytic \
  test_SAR_Calculation \
  test_Automesh \
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
