#!/usr/bin/env bash
# Point the unchanged openEMS M-file interface at the Rust binaries.
#
# `openEMS/matlab/private/invoke_openEMS.m` resolves `openEMS.sh` through
# `searchBinary('openEMS.sh', ...)`, and the checked-in `openEMS/openEMS.sh`
# execs `<repo>/openEMS/openEMS`. That file is a build artifact (gitignored): a
# native build puts the C++ binary there, and the migration links the Rust
# `openems-cli` in its place so the native testsuite drives the Rust solver
# without touching a single M-file.
#
# `CalcNF2FF.m` searches `<repo>/openEMS/nf2ff/nf2ff` first (the native source
# build location), and `CalcSAR.m` searches `<repo>/../bin/sar_calc`. Note that
# the native `searchBinary` concatenates PATH entries without a separator, so a
# PATH lookup never matches; the binaries must sit at the explicit locations.
#
# Usage: scripts/ci/link_rust_openems.sh [--no-build]
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ "${1:-}" != "--no-build" ]; then
  cargo build --release --manifest-path "$REPO_ROOT/Cargo.toml" \
    -p openems-cli -p nf2ff-cli -p sar-cli
fi

link() {
  local target="$REPO_ROOT/target/release/$1"
  local destination="$2"
  if [ ! -x "$target" ]; then
    echo "missing Rust binary: $target" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$destination")"
  ln -sf "$target" "$destination"
  echo "${destination#"$REPO_ROOT"/} -> $target"
}

link openems-cli "$REPO_ROOT/openEMS/openEMS"
link nf2ff-cli "$REPO_ROOT/openEMS/nf2ff/nf2ff"
# The installed layout searches <prefix>/bin, the source tree searches the
# parent of the repository; provide both so either call site resolves.
link nf2ff-cli "$REPO_ROOT/bin/nf2ff"
link sar-cli "$REPO_ROOT/bin/sar_calc"
link sar-cli "$REPO_ROOT/../bin/sar_calc"
