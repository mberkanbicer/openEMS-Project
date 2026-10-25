#!/usr/bin/env bash
# Run the openEMS core tests with the HDF5 feature (field/mode/SAR readers).
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/openEMS/rust"
cargo test --features hdf5 "$@"
