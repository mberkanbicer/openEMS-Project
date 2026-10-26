#!/usr/bin/env bash
# Build the auxiliary openEMS command line tools (nf2ff, sar_calc).
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
cargo build --release -p nf2ff-cli -p sar-cli "$@"
