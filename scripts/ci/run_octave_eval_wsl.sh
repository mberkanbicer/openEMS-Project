#!/usr/bin/env bash
# Run one or more native openEMS Octave tests through the Rust CLI.
set -uo pipefail

REPO_ROOT=/mnt/c/Users/mberkanbicer/.copilot/repos/copilot-worktrees/openEMS-Project/mberkanbicer-potential-garbanzo
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
