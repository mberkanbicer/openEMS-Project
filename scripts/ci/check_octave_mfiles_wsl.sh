#!/usr/bin/env bash
# Check that every CSXCAD/openEMS MATLAB M-file resolves after addpath.
set -uo pipefail

REPO_ROOT=/mnt/c/Users/mberkanbicer/.copilot/repos/copilot-worktrees/openEMS-Project/mberkanbicer-potential-garbanzo
cd "$REPO_ROOT" || exit 1

octave --no-gui --quiet --eval "
addpath('$REPO_ROOT/CSXCAD/matlab');
addpath('$REPO_ROOT/openEMS/matlab');
for tree = {'CSXCAD/matlab', 'openEMS/matlab'}
  root = fullfile('$REPO_ROOT', tree{1});
  files = dir(fullfile(root, '*.m'));
  missing = {};
  for n = 1:numel(files)
    [~, name] = fileparts(files(n).name);
    if exist(name, 'file') == 0
      missing{end+1} = files(n).name;
    end
  end
  printf('%s: %d public M-files, %d missing\n', tree{1}, numel(files), numel(missing));
  if numel(missing) > 0
    printf('   missing: %s\n', strjoin(missing, ', '));
  end
  sub = dir(fullfile(root, 'private', '*.m'));
  printf('%s/private: %d M-files\n', tree{1}, numel(sub));
end
" 2>&1 | grep -v -E "libEGL|MESA|ZINK"
