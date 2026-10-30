#!/usr/bin/env bash
# Full-stack acceptance run (RM-125).
#
# Builds the workspace, runs every unit/integration suite, every differential
# gate and the install-layout check, and writes a markdown report with one row
# per check plus the evidence extracted from each log. A failing check is
# reported as FAIL and makes the script exit non-zero; it never hides a failure.
#
# A check fails when its command exits non-zero *or* when its log carries a
# failure marker, so a gate that only prints "FAIL" cannot be recorded as a
# pass.
#
# Usage: scripts/ci/run_full_acceptance_wsl.sh
#   ACCEPTANCE_REPORT   output path (default: docs/migration/ACCEPTANCE.md)
set -uo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Logs live outside /tmp so a WSL restart does not throw away finished checks,
# and the directory is keyed by the revision: a rerun after a new commit starts
# clean instead of reusing evidence from different code.
# Pin the tested revision once. The report must name the tree that was
# tested, not whatever HEAD happens to be when the report is written after a
# long run.
HEAD_SHA="$(cd "$REPO_ROOT" && git rev-parse HEAD)"
REV="$(cd "$REPO_ROOT" && git rev-parse --short HEAD)"
DIRTY_AT_START=""
if [ -n "$(cd "$REPO_ROOT" && git status --porcelain --untracked-files=no)" ]; then
  REV="$REV-dirty"
  DIRTY_AT_START=" (dirty worktree at start)"
fi
LOG_DIR="${ACCEPTANCE_LOG_DIR:-$HOME/.cache/openems-acceptance/$REV}"
REPORT="${ACCEPTANCE_REPORT:-$REPO_ROOT/docs/migration/ACCEPTANCE.md}"

mkdir -p "$LOG_DIR"

rows=()
failed=0

record() {
  local name="$1"
  local log="$2"
  local summary="$3"
  local status="PASS"
  local code
  code=$(cat "$log.status" 2>/dev/null || echo 1)
  if [ ! -f "$log" ]; then
    status="MISSING"
    failed=$((failed + 1))
  elif [ "$code" -ne 0 ]; then
    status="FAIL"
    failed=$((failed + 1))
  elif grep -qE "FAILED|TESTSUITE FAILED|error: test failed|panicked|check failed" "$log"; then
    status="FAIL"
    failed=$((failed + 1))
  fi
  rows+=("| $name | $status | $summary (exit $code) |")
  printf '%-44s %-4s exit %s\n' "$name" "$status" "$code"
}

run() {
  local name="$1"
  shift
  local log="$LOG_DIR/$(echo "$name" | tr ' /' '__').log"
  # A check that already finished cleanly for this revision is reused, so a
  # restarted run does not repeat the one-hour Octave suite.
  if [ "${ACCEPTANCE_RESUME:-1}" = "1" ] && [ -f "$log.status" ] \
      && [ "$(cat "$log.status" 2>/dev/null)" = "0" ]; then
    echo "cached: $name" >&2
    printf '%s\n' "$log"
    return 0
  fi
  ( cd "$REPO_ROOT" && "$@" ) >"$log" 2>&1
  local code=$?
  printf '%s\n' "$code" >"$log.status"
  printf '%s\n' "$log"
}

sum_passed() {
  local log="$1"
  local total
  total=$(grep -hoE "test result: ok\. [0-9]+ passed" "$log" | grep -oE "[0-9]+" | awk '{s+=$1} END {print s+0}')
  echo "${total:-0} tests passed"
}

sum_unittest() {
  local log="$1"
  local total
  total=$(grep -hoE "^Ran [0-9]+ tests" "$log" | grep -oE "[0-9]+" | awk '{s+=$1} END {print s+0}')
  echo "${total:-0} unittest cases passed"
}

sum_octave() {
  local log="$1"
  grep -hoE "[0-9]+ passed, [0-9]+ failed, [0-9]+ errors" "$log" | tail -1
}

echo "== workspace build"
log=$(run "workspace build" cargo build --workspace --release)
record "workspace build (release)" "$log" "$(grep -c 'Finished' "$log" || true) build(s)"

echo "== crate tests"
log=$(run "crate tests" cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs -p qcsxcad-core -p appcsxcad)
record "crate unit + integration tests" "$log" "$(sum_passed "$log")"

echo "== HDF5 feature"
log=$(run "hdf5 feature" cargo test -p csxcad-core -p openems-core --features hdf5)
record "HDF5 feature tests" "$log" "$(sum_passed "$log")"

echo "== Python packages"
log=$(run "python build" bash scripts/ci/build_rust_python_wsl.sh --release)
record "Python packages build + native imports" "$log" "$(grep -cE 'Installed ' "$log" || true) packages"

log=$(run "python suites" bash scripts/ci/run_rust_python_tests_wsl.sh)
record "native Python suites" "$log" "$(sum_unittest "$log"); $(grep -oE 'SKIPPED: [0-9]+ GPU[^)]*\)' "$log" | tail -1)"

echo "== Octave testsuite (long)"
log=$(run "octave suite" bash scripts/ci/run_octave_testsuite_wsl.sh)
record "native Octave testsuite" "$log" "$(sum_octave "$log")"

echo "== differential gates"
log=$(run "reference harness" bash scripts/ci/run_reference_harness_wsl.sh)
record "differential reference harness" "$log" "$(grep -c '"ok": true' "$log" || true) cases ok"

log=$(run "cylindrical SAR" bash scripts/ci/run_cylindrical_sar_check_wsl.sh)
record "cylindrical SAR differential" "$log" "$(grep -E 'gates:' "$log" | tail -1)"

log=$(run "curve excitation" bash scripts/ci/run_curve_excitation_check_wsl.sh)
record "curve-excitation differential" "$log" "$(grep -E 'ut1x:' "$log" | tail -1)"

echo "== CTB Octave delivery"
log=$(run "ctb build" cargo build -p ctb-rs)
log=$(run "ctb octave" env CTB_BIN="$REPO_ROOT/target/debug/ctb" octave --no-gui --quiet "$REPO_ROOT/CTB/rust/tests/octave/cli_exercise.m")
record "CTB Octave delivery" "$log" "$(grep -E 'CTB CLI Octave exercise' "$log" | tail -1)"

echo "== install layout and records"
log=$(run "cmake install layout" bash scripts/ci/check_cmake_install.sh)
record "CMake install layout" "$log" "$(grep -E 'CMake install layout' "$log" | tail -1)"

log=$(run "migration records" python3 scripts/ci/check_migration_docs.py)
record "migration records" "$log" "check passed"

log=$(run "placeholder policy" python3 scripts/ci/check_placeholders.py --self-test)
record "placeholder policy self-test" "$log" "self-test passed"

echo
echo "== report: $REPORT"
{
  echo "# Full-stack acceptance run (RM-125)"
  echo
  echo "Generated by \`scripts/ci/run_full_acceptance_wsl.sh\` on $(date -u '+%Y-%m-%d %H:%M UTC')."
  echo "Repository revision: \`$HEAD_SHA\`$DIRTY_AT_START."
  echo
  echo "A check counts as PASS only when its command exits 0 and its log carries"
  echo "no failure marker."
  echo
  echo "| Check | Result | Evidence |"
  echo "| --- | --- | --- |"
  for row in "${rows[@]}"; do
    echo "$row"
  done
  echo
  if [ "$failed" -eq 0 ]; then
    echo "**All checks passed.**"
  else
    echo "**$failed check(s) failed** -- this report is not an acceptance."
  fi
} > "$REPORT"

if [ "$failed" -ne 0 ]; then
  echo "acceptance run: FAIL ($failed)" >&2
  exit 1
fi
echo "acceptance run: PASS"
