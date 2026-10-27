#!/usr/bin/env bash
# Build and install the Rust Python extensions for the WSL validation runs.
#
# The native Python test suites need `CSXCAD` and `openEMS` importable next to
# numpy/h5py. This script prepares a virtual environment with the system
# packages visible and installs both PyO3 extensions with maturin, so the
# suites can run unchanged against the Rust core.
#
# Usage: scripts/ci/build_rust_python_wsl.sh [--release|--debug]
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

MODE="${1:---release}"
case "$MODE" in
  --release|--debug) ;;
  *)
    echo "usage: $0 [--release|--debug]" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"

if [ ! -x "$VENV/bin/python" ]; then
  echo "creating $VENV (system site packages visible for numpy/h5py)"
  python3 -m venv --system-site-packages "$VENV"
fi

if ! "$VENV/bin/python" -c "import maturin" >/dev/null 2>&1; then
  echo "installing maturin into $VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade maturin
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

for crate in CSXCAD/rust-py openEMS/rust-py; do
  echo "building $crate"
  ( cd "$REPO_ROOT/$crate" && maturin develop "$MODE" )
done

export PYTHONPATH="$REPO_ROOT/CSXCAD/rust-py/python:$REPO_ROOT/openEMS/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"

# RM-013: the installed packages must be importable with the native names and
# without PYTHONPATH, exactly like the Cython/Python originals.
( cd /tmp && env -u PYTHONPATH python - <<'PY'
from CSXCAD import ContinuousStructure
from openEMS import openEMS
import CSXCAD
import csxcad_py
import openEMS as openems_package
from openEMS import _openems

print("CSXCAD:", CSXCAD.__file__, CSXCAD.__version__)
print("openEMS:", openems_package.__file__, openems_package.__version__)
print("csxcad_py:", csxcad_py.__file__)
print("_openems:", _openems.__file__)
print("grid:", type(ContinuousStructure().GetGrid()).__name__)
print("solver:", openEMS)
PY
)
echo "Rust Python extensions installed in $VENV"
