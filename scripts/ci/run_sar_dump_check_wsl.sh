#!/usr/bin/env bash
# Validate the raw SAR dump + sar_calc path end to end.
#
# Runs a small lossy-box simulation through the Octave interface with a
# `DumpType` 29 dump, processes it with `sar_calc` and compares the local SAR
# against sigma|E|^2/(2 rho) evaluated from the raw dump itself.
set -euo pipefail

REPO_ROOT=/mnt/c/Users/mberkanbicer/.copilot/repos/copilot-worktrees/openEMS-Project/mberkanbicer-potential-garbanzo
export PATH="$REPO_ROOT/bin:$PATH"
cd "$REPO_ROOT/openEMS/TESTSUITE"

rm -rf tmp_sarcheck
mkdir -p tmp_sarcheck

octave --no-gui --quiet --eval "
addpath('$REPO_ROOT/CSXCAD/matlab');
addpath('$REPO_ROOT/openEMS/matlab');
physical_constants;
unit = 1e-3;
Sim_Path = 'tmp_sarcheck';
CSX = InitCSX();
mesh.x = 0:2:20;
mesh.y = 0:2:20;
mesh.z = 0:2:20;
CSX = DefineRectGrid(CSX, unit, mesh);
CSX = AddMaterial(CSX, 'lossy');
CSX = SetMaterialProperty(CSX, 'lossy', 'Epsilon', 10, 'Kappa', 0.5, 'Density', 1000);
CSX = AddBox(CSX, 'lossy', 1, [2 2 2], [18 18 18]);
CSX = AddExcitation(CSX, 'ex', 1, [0 0 1]);
CSX = AddBox(CSX, 'ex', 1, [8 8 8], [12 12 12]);
CSX = AddDump(CSX, 'sar_raw', 'DumpType', 29, 'DumpMode', 2, 'FileType', 1, 'Frequency', 1e9);
CSX = AddBox(CSX, 'sar_raw', 1, [2 2 2], [18 18 18]);
FDTD = InitFDTD('NrTS', 800, 'EndCriteria', 1e-6);
FDTD = SetGaussExcite(FDTD, 1e9, 0.5e9);
FDTD = SetBoundaryCond(FDTD, repmat({'PEC'}, 1, 6));
WriteOpenEMS([Sim_Path '/sarcheck.xml'], FDTD, CSX);
Settings.LogFile = 'sarcheck.log';
Settings.Silent = 0;
RunOpenEMS(Sim_Path, 'sarcheck.xml', '', Settings);
" >/dev/null

cd tmp_sarcheck
"$REPO_ROOT/bin/sar_calc" -i sar_raw.h5 -o sar_local.h5 --mass 0 >/dev/null
"${RUSTPY_VENV:-$HOME/rustpy-venv}/bin/python" - <<'PY'
import h5py
import numpy as np

with h5py.File("sar_raw.h5", "r") as raw:
    field = raw["FieldData/FD/f0"][:]
    density = raw["CellData/Density"][:]
    conductivity = raw["CellData/Conductivity"][:]
    volume = raw["CellData/Volume"][:]
    frequency = raw["FieldData/FD"].attrs["frequency"]

assert field.shape[0] == 3 and field.shape[1:] == density.shape
assert np.any(density > 0.0) and np.any(conductivity > 0.0)
assert volume.sum() > 0.0
assert abs(float(frequency[0]) - 1.0e9) < 1.0

with h5py.File("sar_local.h5", "r") as result:
    sar = result["FieldData/FD/f0"][:]
    stored = float(result["FieldData/FD/f0"].attrs["maxSAR"])

power_density = 0.5 * conductivity * np.sum(np.abs(field) ** 2, axis=0)
local = np.divide(power_density, density, out=np.zeros_like(power_density), where=density > 0)
peak = float(np.max(local))
deviation = abs(float(np.max(sar)) - peak) / peak
print(f"SAR raw dump + sar_calc: peak {peak:.6e} W/kg, deviation {deviation:.3e}")
assert deviation < 1.0e-6, deviation
assert abs(stored - float(np.max(sar))) <= 1.0e-6 * peak
print("SAR dump check passed")
PY
