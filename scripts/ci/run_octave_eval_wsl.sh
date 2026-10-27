#!/usr/bin/env bash
# Run one or more native openEMS Octave tests through the Rust binaries.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PATH="$REPO_ROOT/bin:$PATH"
bash "$SCRIPT_DIR/link_rust_openems.sh" --no-build >/dev/null || exit 1
cd "$REPO_ROOT/openEMS/TESTSUITE" || exit 1

octave --no-gui --quiet --eval "
addpath('$REPO_ROOT/CSXCAD/matlab');
addpath('$REPO_ROOT/openEMS/matlab');
addpath('$REPO_ROOT/openEMS/TESTSUITE/helperscripts');
addpath('$REPO_ROOT/openEMS/TESTSUITE/combinedtests');
addpath('$REPO_ROOT/openEMS/TESTSUITE/unittests');
addpath('$REPO_ROOT/openEMS/TESTSUITE/probes');
addpath('$REPO_ROOT/openEMS/TESTSUITE/enginetests');
$*
" 2>&1
