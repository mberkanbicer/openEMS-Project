#!/usr/bin/env bash
# Prepare the Octave/MATLAB interface to run against the Rust binaries.
#
# The native M-files locate the solver through `openEMS.sh` next to the openEMS
# source root and the helper tools through their source folders or PATH; the
# Rust binaries are linked under the native names.
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

"$SCRIPT_DIR/build_openems_cli_wsl.sh"
"$SCRIPT_DIR/build_openems_tools_wsl.sh"

TARGET="$REPO_ROOT/target/release"

# openEMS solver
if [ ! -x "$TARGET/openems-cli" ]; then
  echo "missing Rust CLI binary: $TARGET/openems-cli" >&2
  exit 1
fi
ln -sf "$TARGET/openems-cli" "$REPO_ROOT/openEMS/openEMS"
chmod +x "$REPO_ROOT/openEMS/openEMS.sh"

# nf2ff transform (searched next to the sources)
if [ ! -x "$TARGET/nf2ff-cli" ]; then
  echo "missing Rust nf2ff binary: $TARGET/nf2ff-cli" >&2
  exit 1
fi
ln -sf "$TARGET/nf2ff-cli" "$REPO_ROOT/openEMS/nf2ff/nf2ff"

# SAR calculation (searched on PATH, installed into <repo>/bin)
if [ ! -x "$TARGET/sar-cli" ]; then
  echo "missing Rust sar_calc binary: $TARGET/sar-cli" >&2
  exit 1
fi
mkdir -p "$REPO_ROOT/bin"
ln -sf "$TARGET/sar-cli" "$REPO_ROOT/bin/sar_calc"

echo "openEMS -> $TARGET/openems-cli"
echo "nf2ff   -> $TARGET/nf2ff-cli"
echo "sar_calc -> $TARGET/sar-cli"
