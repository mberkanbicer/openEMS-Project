#!/usr/bin/env bash
# Run the complete native openEMS Octave testsuite through the Rust binaries.
set -uo pipefail

REPO_ROOT=/mnt/c/Users/mberkanbicer/.copilot/repos/copilot-worktrees/openEMS-Project/mberkanbicer-potential-garbanzo
export PATH="$REPO_ROOT/bin:$PATH"
cd "$REPO_ROOT/openEMS/TESTSUITE" || exit 1

octave --no-gui --quiet --eval "
addpath('$REPO_ROOT/CSXCAD/matlab');
addpath('$REPO_ROOT/openEMS/matlab');
addpath('$REPO_ROOT/openEMS/TESTSUITE');
run_testsuite
" 2>&1
