#!/usr/bin/env bash
# Type-check the CSXCAD Python extension crate inside WSL.
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/CSXCAD/rust-py"
cargo check --message-format short "$@"
