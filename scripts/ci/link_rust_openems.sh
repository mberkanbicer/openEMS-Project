#!/usr/bin/env bash
# Point the unchanged openEMS M-file interface at the Rust CLI.
#
# `openEMS/matlab/private/invoke_openEMS.m` resolves `openEMS.sh` through
# `searchBinary('openEMS.sh', ...)`, and the checked-in `openEMS/openEMS.sh`
# execs `<repo>/openEMS/openEMS`. That file is a build artifact (gitignored): a
# native build puts the C++ binary there, and the migration links the Rust
# `openems-cli` in its place so the native testsuite drives the Rust solver
# without touching a single M-file.
#
# Usage: scripts/ci/link_rust_openems.sh [--no-build]
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ "${1:-}" != "--no-build" ]; then
  cargo build --release --manifest-path "$REPO_ROOT/Cargo.toml" -p openems-cli
fi

TARGET="$REPO_ROOT/target/release/openems-cli"
if [ ! -x "$TARGET" ]; then
  echo "missing Rust solver: $TARGET" >&2
  exit 1
fi

ln -sf "$TARGET" "$REPO_ROOT/openEMS/openEMS"
echo "openEMS/openEMS -> $TARGET"
