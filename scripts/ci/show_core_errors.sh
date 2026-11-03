#!/usr/bin/env bash
# Show the compile errors of the CSXCAD core crate inside WSL.
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/CSXCAD/rust"
cargo test --message-format short 2>&1 | grep -E "error" | head -20
