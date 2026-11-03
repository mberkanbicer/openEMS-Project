#!/usr/bin/env bash
# Validate the raw SAR dump + sar_calc path end to end.
#
# Runs a small lossy-box simulation through the Octave interface with a
# `DumpType` 29 dump, processes it with `sar_calc` and compares the local SAR
# against sigma|E|^2/(2 rho) evaluated from the raw dump itself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PATH="$REPO_ROOT/bin:$PATH"
bash "$SCRIPT_DIR/link_rust_openems.sh" --no-build >/dev/null || exit 1
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
CSX = AddDump(CSX, 'sar_direct', 'DumpType', 20, 'DumpMode', 2, 'FileType', 1, 'Frequency', 1e9);
CSX = AddBox(CSX, 'sar_direct', 1, [2 2 2], [18 18 18]);
CSX = AddDump(CSX, 'sar_direct_1g', 'DumpType', 21, 'DumpMode', 2, 'FileType', 1, 'Frequency', 1e9);
CSX = AddBox(CSX, 'sar_direct_1g', 1, [2 2 2], [18 18 18]);
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

# The direct result dump (DumpType 20) uses the native J-field path
# (kappa at the Yee-edge position), while the raw dump + sar_calc path uses
# the cell-centre conductivity. Inside a homogeneous region both give exactly
# the same value; the first/last material layer differs because the edge
# kappa is averaged over quarter cells that lie partly outside the box
# (native has the same distinction, and warns for unisotropic material).
with h5py.File("sar_direct.h5", "r") as direct:
    direct_sar = direct["FieldData/FD/f0"][:]
    direct_max = float(direct["FieldData/FD/f0"].attrs["maxSAR"])
assert direct_sar.shape == sar.shape, (direct_sar.shape, sar.shape)
scale = max(float(np.max(np.abs(sar))), 1.0e-300)
peak_difference = abs(direct_max - float(np.max(sar))) / scale
inner = np.s_[3:8, 3:8, 3:8]
inner_difference = float(np.max(np.abs(direct_sar[inner] - sar[inner]))) / scale
outer_difference = float(np.max(np.abs(direct_sar - sar))) / scale
print(f"direct DumpType 20 vs raw+sar_calc: peak {peak_difference:.3e}, "
      f"homogeneous interior {inner_difference:.3e}, whole block {outer_difference:.3e}")
assert peak_difference < 1.0e-6, peak_difference
assert inner_difference < 1.0e-6, inner_difference
assert outer_difference < 1.5e-2, outer_difference
assert abs(direct_max - stored) <= 1.0e-5 * scale

# 1 g averaging runs in the solver through the same SAR_Calculation.
with h5py.File("sar_direct_1g.h5", "r") as averaged:
    averaged_sar = averaged["FieldData/FD/f0"][:]
    averaged_max = float(averaged["FieldData/FD/f0"].attrs["maxSAR"])
    assert float(averaged.attrs["mass"]) > 0.0
assert averaged_max > 0.0
assert averaged_max <= float(np.max(sar)) * (1.0 + 1.0e-6)
print(f"1 g averaged dump: maxSAR {averaged_max:.6e} W/kg")
print("SAR dump check passed")
PY
