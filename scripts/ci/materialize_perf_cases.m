function materialize_perf_cases(out_dir, varargin)
%materialize_perf_cases(out_dir, <case>, ...)
%
% Write the FDTD input XML of the given openEMS testsuite cases into
% <out_dir>/<case>.xml without running a solver.
%
% The cases are the *unmodified* testsuite sources from
% openEMS/TESTSUITE/combinedtests. Each one is copied into <out_dir>/cases and
% executed with a stub RunOpenEMS that aborts the test right after
% WriteOpenEMS, so the XML is byte-for-byte the input the testsuite itself
% would hand to the solver. Both the native and the Rust solver of the
% RM-121/RM-122 performance baseline then run on that same file.
%
% Usage (from the repository root):
%
%   octave --no-gui --quiet --eval \
%     "addpath('scripts/ci'); materialize_perf_cases('/tmp/perf/cases')"
%
% openEMS Rust migration -- RM-121/RM-122

  if nargin < 1
    error('perf:usage', 'materialize_perf_cases: an output directory is required');
  end

  if nargin > 1
    cases = varargin;
  else
    cases = {'cavity', 'Coax', 'msl_port'};
  end

  repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
  test_dir = fullfile(repo_root, 'openEMS', 'TESTSUITE', 'combinedtests');
  helpers  = fullfile(repo_root, 'openEMS', 'TESTSUITE', 'helperscripts');

  if exist('OCTAVE_VERSION', 'builtin') == 5
    confirm_recursive_rmdir(false);
  end

  if ~exist(out_dir, 'dir')
    [ok, msg] = mkdir(out_dir);
    if ~ok
      error('perf:io', 'cannot create %s: %s', out_dir, msg);
    end
  end

  % The case sources resolve their helpers relative to their own location
  % (<parent>/helperscripts), so mirror the testsuite layout instead of
  % relying on a path that only works inside the source tree.
  local_helpers = fullfile(out_dir, 'helperscripts');
  if exist(local_helpers, 'dir')
    rmdir(local_helpers, 's');
  end
  copyfile(helpers, local_helpers);

  addpath(local_helpers);
  addpath(fullfile(repo_root, 'CSXCAD', 'matlab'));
  addpath(fullfile(repo_root, 'openEMS', 'matlab'));

  work_dir = fullfile(out_dir, 'src');
  stub_dir = fullfile(out_dir, 'stub');
  if exist(work_dir, 'dir')
    rmdir(work_dir, 's');
  end
  if exist(stub_dir, 'dir')
    rmdir(stub_dir, 's');
  end
  mkdir(work_dir);
  mkdir(stub_dir);

  % A stub that stops the test after WriteOpenEMS: the solver must not run.
  stub_file = fullfile(stub_dir, 'RunOpenEMS.m');
  fid = fopen(stub_file, 'w');
  if fid < 0
    error('perf:io', 'cannot write %s', stub_file);
  end
  fprintf(fid, 'function RunOpenEMS(varargin)\n');
  fprintf(fid, '  error(''perf:materialized'', ''PERF_MATERIALIZED'');\n');
  fprintf(fid, 'end\n');
  fclose(fid);
  addpath(stub_dir, '-begin');

  for n = 1:numel(cases)
    name = cases{n};
    source = fullfile(test_dir, [name '.m']);
    if exist(source, 'file') ~= 2
      error('perf:missing', 'testsuite case not found: %s', source);
    end
    target = fullfile(work_dir, [name '.m']);
    copyfile(source, target);

    sim_path = fullfile(work_dir, ['tmp_' name]);
    addpath(work_dir, '-begin');
    materialized = false;
    try
      feval(name, 'Plots', 0, 'Silent', 1, 'Verbose', 0, 'StopIfFailed', 0);
    catch err
      if ~strcmp(err.identifier, 'perf:materialized')
        rethrow(err);
      end
      materialized = true;
    end
    if ~materialized
      error('perf:materialized', '%s never called RunOpenEMS', name);
    end

    listing = dir(fullfile(sim_path, '*.xml'));
    if numel(listing) ~= 1
      error('perf:materialized', '%s wrote %d XML files, expected 1', ...
            name, numel(listing));
    end
    copyfile(fullfile(sim_path, listing(1).name), ...
             fullfile(out_dir, [name '.xml']));
    rmdir(sim_path, 's');
    fprintf('materialized %s.xml from %s\n', name, [name '.m']);
  end

  rmpath(work_dir);
  rmpath(stub_dir);
end
