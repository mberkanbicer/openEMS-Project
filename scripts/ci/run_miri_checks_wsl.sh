#!/usr/bin/env bash
# Miri memory-safety checks for the parser and operator crates (RM-180).
#
# Miri emulates floating point with its own implementation, so the parser's
# exact-parity tests that compare the last bit of sqrt/exp/log compositions are
# excluded. The excluded names are listed below and in VALIDATION.md; every
# other parser test plus the operator timestep tests run under Miri.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if ! cargo +nightly miri --version >/dev/null 2>&1; then
  echo "Miri is not installed; run: rustup component add --toolchain nightly miri"
  exit 2
fi

# Exact last-bit floating-point parity tests of the optimizer: Miri's float
# emulation differs from the host for these transcendentals (observed diffs are
# in the log). They are excluded as a group; the parser/evaluator tests and the
# operator tests still run.
SKIP_ARGS=(--skip optimization --skip optimized)

echo "== Miri: fparser-rs"
cargo +nightly miri test -p fparser-rs -- "${SKIP_ARGS[@]}"

echo "== Miri: openems-core operator tests"
cargo +nightly miri test -p openems-core --lib \
  operator::timestep_tests::var1_and_var3_match_the_uniform_mesh_analytic_values
cargo +nightly miri test -p openems-core --lib \
  operator::timestep_tests::var3_is_larger_than_var1_on_a_nonuniform_mesh
cargo +nightly miri test -p openems-core --lib \
  operator::coordinate_system_tests::cylindrical_r0_uses_the_conservative_timestep

echo "Miri checks passed"
