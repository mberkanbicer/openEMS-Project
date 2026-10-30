% MATLAB smoke for the M-file interface -> Rust CLI.
%
% Run from the repository root (the built CLI must be at openEMS/openEMS.exe):
%   matlab -batch "run('scripts/ci/matlab_smoke.m')"
%
% It builds a small PEC cavity, writes the openEMS XML with the CSXCAD M-files,
% runs a setup-only pass and a 50-step simulation through RunOpenEMS, and
% prints PASS when both return.

here = fileparts(mfilename('fullpath'));       % .../scripts/ci
root = fileparts(fileparts(here));             % repository root
addpath(fullfile(root, 'CSXCAD', 'matlab'));
addpath(fullfile(root, 'openEMS', 'matlab'));

sim = fullfile(tempdir, 'matlab_openems_smoke');
if exist(sim, 'dir')
    rmdir(sim, 's');
end
mkdir(sim);

CSX = InitCSX();
mesh.x = linspace(0, 50, 11);
mesh.y = linspace(0, 20, 6);
mesh.z = linspace(0, 30, 8);
CSX = DefineRectGrid(CSX, 1e-3, mesh);
CSX = AddMetal(CSX, 'metal');
CSX = AddBox(CSX, 'metal', 10, [0 0 0], [50 20 0]);

FDTD = InitFDTD('NrTS', 50, 'EndCriteria', 0);
FDTD = SetBoundaryCond(FDTD, {'PEC', 'PEC', 'PEC', 'PEC', 'PEC', 'PEC'});
FDTD = SetGaussExcite(FDTD, 1e9, 1e9);
xml = fullfile(sim, 'smoke.xml');
WriteOpenEMS(xml, FDTD, CSX);

info = dir(xml);
fprintf('MATLAB smoke: wrote %s (%d bytes)\n', xml, info.bytes);

Settings = struct('Silent', 1);
RunOpenEMS(sim, 'smoke.xml', '--no-simulation', Settings);
fprintf('MATLAB smoke: no-simulation setup returned\n');
RunOpenEMS(sim, 'smoke.xml', '', Settings);
fprintf('MATLAB smoke: 50-step simulation returned\n');
disp('MATLAB smoke: PASS');
