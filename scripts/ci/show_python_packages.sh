#!/usr/bin/env bash
# Print the versions of the Python packages the native test suites rely on.
set -uo pipefail

PYTHON="${1:-python3}"

"$PYTHON" - <<'PY'
import importlib

for name in ("numpy", "h5py", "scipy", "matplotlib"):
    try:
        module = importlib.import_module(name)
    except ImportError as error:
        print(f"{name}: missing ({error})")
    else:
        print(f"{name}: {getattr(module, '__version__', 'unknown')}")
PY
