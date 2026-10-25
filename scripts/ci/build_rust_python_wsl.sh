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

python - <<'PY'
import csxcad_py
import openems_py

print("csxcad_py:", csxcad_py.__file__)
print("openems_py:", openems_py.__file__)
PY
echo "Rust Python extensions installed in $VENV"
