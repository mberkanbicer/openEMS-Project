#!/usr/bin/env bash
# Prepare the Octave/MATLAB interface to run against the Rust CLI.
#
# The native M-files locate the solver through `openEMS.sh` next to the openEMS
# source root; the Rust CLI is linked there under the native binary name.
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

"$SCRIPT_DIR/build_openems_cli_wsl.sh"

# the Cargo workspace lives at the repository root
BINARY="$REPO_ROOT/target/release/openems-cli"
LINK="$REPO_ROOT/openEMS/openEMS"

if [ ! -x "$BINARY" ]; then
  echo "missing Rust CLI binary: $BINARY" >&2
  exit 1
fi

ln -sf "$BINARY" "$LINK"
chmod +x "$REPO_ROOT/openEMS/openEMS.sh"
echo "openEMS -> $BINARY"
