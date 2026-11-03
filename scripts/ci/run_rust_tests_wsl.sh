#!/usr/bin/env bash
# Run the Rust test suites of the workspace crates inside WSL.
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/crates/csxcad-core"
cargo test
# the HDF5 backed readers (discrete materials, mode files) need the feature
cargo test --features hdf5

cd "$REPO_ROOT/crates/openems-core"
cargo test

cd "$REPO_ROOT/crates/fparser"
cargo test

cd "$REPO_ROOT/crates/hyp2mat"
cargo test
