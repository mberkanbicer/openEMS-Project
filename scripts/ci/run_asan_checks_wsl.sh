#!/usr/bin/env bash
# AddressSanitizer pass for the parser and operator crates (RM-183).
#
# Rust needs a nightly toolchain, the rust-src component and -Zbuild-std so the
# standard library is instrumented too. ASan enlarges stack frames, so the test
# threads get a 64 MiB stack; otherwise the parser's deliberate 4000-level
# nesting test exhausts the default 8 MiB before the parser's own depth guard
# fires (that is stack pressure from instrumentation, not a memory error).
#
# Usage: scripts/ci/run_asan_checks_wsl.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

export RUST_MIN_STACK=67108864
export RUSTFLAGS="-Zsanitizer=address"

echo "== ASan: fparser-rs"
cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu -p fparser-rs

echo "== ASan: openems-core operator tests"
cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu \
  -p openems-core --lib operator::

echo "ASan checks passed"
