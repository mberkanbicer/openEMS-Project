#!/usr/bin/env bash
# Compile the openEMS core crate and show errors only.
set -uo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/openEMS/rust"
cargo test --no-run --message-format short 2>&1 | grep -E "error" | head -20
