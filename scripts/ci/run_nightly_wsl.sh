#!/usr/bin/env bash
# Nightly reference run (RM-124).
#
# Runs the crate tests and the 51-case differential reference harness and keeps
# a dated artifact under docs/migration/reference-data/nightly/.
#
# GitHub Actions is unavailable for this repository, so the same job is
# installed as a Windows Task Scheduler entry (`openEMS-nightly-reference`,
# daily 03:00) which calls this script through WSL. The artifact records the
# UTC date and the exit status of every stage.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATE="$(date -u +%Y-%m-%d)"
OUT="$REPO_ROOT/docs/migration/reference-data/nightly/$DATE"
mkdir -p "$OUT"

export PATH="$HOME/.cargo/bin:$PATH"
cd "$REPO_ROOT" || exit 1

status=0
echo "nightly reference run $DATE $(date -u +%H:%M:%SZ)" > "$OUT/README.md"
echo >> "$OUT/README.md"

cargo test -p openems-core --features hdf5 --release > "$OUT/crates.log" 2>&1
crates=$?
echo "- crate tests: $([ $crates -eq 0 ] && echo PASS || echo FAIL)" >> "$OUT/README.md"
[ $crates -eq 0 ] || status=1

bash "$SCRIPT_DIR/run_reference_harness_wsl.sh" > "$OUT/reference.log" 2>&1
reference=$?
echo "- reference harness: $([ $reference -eq 0 ] && echo PASS || echo FAIL)" >> "$OUT/README.md"
[ $reference -eq 0 ] || status=1

echo "- exit: $status" >> "$OUT/README.md"
echo "nightly reference run finished with status $status"
exit $status
