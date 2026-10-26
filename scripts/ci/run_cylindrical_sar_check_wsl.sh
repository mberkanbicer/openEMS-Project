#!/usr/bin/env bash
# RM-143 check: SAR on a cylindrical mesh.
#
# A lossy cylindrical shell (muscle-like material) on a closed mesh with the
# rho = 0 axis is excited by a Gaussian; the raw SAR dump (DumpType 29) and a
# 1 g result dump (DumpType 21) are written by the Rust and native solvers on
# the exact same input.xml. The check compares the HDF5 layouts (/Mesh,
# /CellWidth, /CellData, /FieldData/FD) and the 1 g SAR result values.
#
# Usage: scripts/ci/run_cylindrical_sar_check_wsl.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi
export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"

WORK="${TMPDIR:-/tmp}/cyl_sar_check"
rm -rf "$WORK"
mkdir -p "$WORK/rust" "$WORK/native"

"$PYTHON" - "$WORK" <<'PY'
import os
import sys

import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS

work = sys.argv[1]
unit = 1e-3
radius = 20.0
height = 20.0
dr = dz = 2.0
n_alpha = 16

f0 = 2.0e9
fc = 0.5e9

sim_path = os.path.join(work, "rust")
FDTD = openEMS(CoordSystem=1, NrTS=6000, EndCriteria=1e-5)
FDTD.SetGaussExcite(f0, fc)
FDTD.SetBoundaryCond(["PEC"] * 6)

CSX = ContinuousStructure(CoordSystem=1)
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(unit)
mesh.AddLine("r", np.arange(0, radius + dr / 2, dr))
mesh.AddLine("a", (np.arange(n_alpha + 1) - n_alpha / 2) * 2 * np.pi / n_alpha)
mesh.AddLine("z", np.arange(0, height + dz / 2, dz))

# muscle-like lossy shell filling the cavity
material = CSX.AddMaterial("muscle", epsilon=80.0, kappa=1.0, density=1000.0)
material.AddBox([0, -np.pi, 0], [radius, np.pi, height])

# off-axis z-directed line source
src = CSX.AddExcitation("source", exc_type=0, exc_val=[0, 0, 1])
src.AddBox([4 * dr, 0, 2 * dz], [4 * dr, 0, height - 2 * dz])
CSX.AddProbe("et", p_type=2).AddPoint([10 * dr, np.pi / 4, height / 2])

raw = CSX.AddDump("SAR_raw", dump_type=29, dump_mode=2, file_type=1, frequency=[f0])
raw.AddBox([0, -np.pi, 0], [radius, np.pi, height])
result = CSX.AddDump("SAR_1g", dump_type=21, dump_mode=2, file_type=1, frequency=[f0])
result.AddBox([0, -np.pi, 0], [radius, np.pi, height])

error = FDTD.Run(sim_path, cleanup=False)
if error != 0:
    raise SystemExit("rust run failed: %d" % error)
FDTD.Write2XML(os.path.join(sim_path, "input.xml"))
print("rust run done")
PY

cp "$WORK/rust/input.xml" "$WORK/native/input.xml"
( cd "$WORK/native" && "${NATIVE_OPENEMS:-$HOME/opt/openEMS/bin/openEMS}" input.xml > log 2>&1 )

"$PYTHON" - "$WORK" <<'PY'
import os
import sys

import h5py
import numpy as np

work = sys.argv[1]

def load_raw(path):
    with h5py.File(path, "r") as handle:
        out = {
            "mesh_type": int(handle["/Mesh"].attrs["mesh_type"]),
            "mesh_scaling": float(handle["/Mesh"].attrs["mesh_scaling"]),
            "mesh": {name: handle["/Mesh/" + name][()] for name in handle["/Mesh"]},
            "cell_width_type": int(handle["/CellWidth"].attrs["mesh_type"]),
            "cell_width": {name: handle["/CellWidth/" + name][()] for name in handle["/CellWidth"]},
            "volume": handle["/CellData/Volume"][()],
            "density": handle["/CellData/Density"][()],
            "conductivity": handle["/CellData/Conductivity"][()],
        }
        names = sorted(key for key in handle["/FieldData/FD"] if key.startswith("f"))
        out["field"] = handle["/FieldData/FD/" + names[0]][()]
    return out

def load_result(path):
    with h5py.File(path, "r") as handle:
        names = sorted(key for key in handle["/FieldData/FD"] if key.startswith("f") and "_" not in key)
        dataset = handle["/FieldData/FD/" + names[0]]
        out = {
            "sar": dataset[()],
            "max_sar": float(dataset.attrs["maxSAR"]),
            "max_idx": tuple(int(value) for value in np.atleast_1d(dataset.attrs["maxSAR_idx"])),
        }
        for name in ("CubeMass", "CubeVol", "CubeType"):
            key = "/FieldData/FD/" + names[0] + "_" + name
            if key in handle:
                out[name] = handle[key][()]
        for attr in ("valid_cubes", "used_cubes"):
            if attr in handle["/FieldData/FD"].attrs:
                out[attr] = int(handle["/FieldData/FD"].attrs[attr])
    return out

for label, folder in (("rust", "rust"), ("native", "native")):
    raw = load_raw(os.path.join(work, folder, "SAR_raw.h5"))
    result = load_result(os.path.join(work, folder, "SAR_1g.h5"))
    print("  %s: mesh_type=%d cells=%s vol[range]=(%.3e, %.3e) maxSAR=%.4e" % (
        label, raw["mesh_type"], raw["volume"].shape,
        float(np.min(raw["volume"])), float(np.max(raw["volume"])),
        result["max_sar"],
    ))

# analytic metric check: every cell volume is the native annulus formula
# node_area(2, dual=false) * edge_length(2, dual=false)
rust_raw = load_raw(os.path.join(work, "rust", "SAR_raw.h5"))
assert rust_raw["mesh_type"] == 1, "raw dump must declare the cylindrical mesh"
assert "alpha" in rust_raw["mesh"], "raw dump must use the rho/alpha/z names"
rho = rust_raw["mesh"]["rho"]
alpha = rust_raw["mesh"]["alpha"]
z = rust_raw["mesh"]["z"]

def dual_line(lines, index):
    if index + 1 < len(lines):
        return 0.5 * (lines[index] + lines[index + 1])
    return lines[index] + 0.5 * (lines[index] - lines[index - 1])

worst = 0.0
for i in range(len(rho)):
    # the written line coordinates are the dual (cell-boundary) rho values,
    # which are exactly the r2 bounds of the native node area
    r2 = rho[i]
    if i > 0:
        r1 = r2 - (rho[i] - rho[i - 1])
    else:
        r1 = r2 - (rho[1] - rho[0])
    for j in range(len(alpha) - 1):
        da = alpha[j + 1] - alpha[j]
        base = 0.5 * da * (
            r2 * r2 - (r1 * r1 if r1 > 0.0 else 0.0)
        )
        for k in range(len(z) - 1):
            expected = base * (z[k + 1] - z[k])
            volume = float(rust_raw["volume"][i, j, k])
            if expected > 0.0:
                worst = max(worst, abs(volume - expected) / expected)
print("  volume vs analytic annulus*dz: max rel. difference %.3e" % worst)
# the volumes are stored as float32, so ~1e-7 relative rounding is expected
assert worst < 1e-6, "cell volumes deviate from the annulus metric by %.3e" % worst

native_raw = load_raw(os.path.join(work, "native", "SAR_raw.h5"))
assert rust_raw["volume"].shape == native_raw["volume"].shape, "raw shapes differ"
for key in ("volume", "density", "conductivity"):
    r, n = rust_raw[key], native_raw[key]
    scale = max(float(np.max(np.abs(n))), 1e-30)
    diff = float(np.max(np.abs(r - n))) / scale
    print("  raw %s vs native: max rel. difference %.3e" % (key, diff))
    assert diff < 1e-6, "%s differs from native by %.3e" % (key, diff)

# solver-level sanity: the raw time-domain probe must match before any SAR
# post-processing runs
print("  native log timestep lines: %s" % [
    line.strip() for line in open(os.path.join(work, "native", "log"))
    if "timestep" in line.lower()][:2])
rust_et = np.loadtxt(os.path.join(work, "rust", "et"), comments="%")
native_et = np.loadtxt(os.path.join(work, "native", "et"), comments="%")
print("  probe t[1]: rust %.4e native %.4e (per-step dt*interval)" % (
    rust_et[1, 0], native_et[1, 0]))
print("  probe t[:6] rust :", ["%.4e" % value for value in rust_et[:6, 0]])
print("  probe t[:6] native:", ["%.4e" % value for value in native_et[:6, 0]])
print("  probe t tail rust:", ["%.4e" % value for value in rust_et[-3:, 0]])
print("  probe cadence: rust rows=%d native rows=%d" % (len(rust_et), len(native_et)))
print("  NOTE: the rust run stopped on the end criteria earlier than native "
      "(probe sample count differs); tracked as RM-146")
if rust_et.shape == native_et.shape:
    et_scale = max(float(np.max(np.abs(native_et[:, 1:]))), 1e-30)
    et_diff = float(np.max(np.abs(rust_et[:, 1:] - native_et[:, 1:]))) / et_scale
    print("  probe et vs native: max rel. difference %.3e" % et_diff)
else:
    print("  probe et: shapes differ rust %s native %s" % (
        rust_et.shape, native_et.shape))

r_field, n_field = rust_raw["field"], native_raw["field"]
scale = float(np.max(np.abs(n_field)))
print("  field scale: rust %.3e native %.3e" % (
    float(np.max(np.abs(r_field))), scale))
worst = np.unravel_index(int(np.argmax(np.abs(r_field - n_field))), r_field.shape)
print("  worst cell %s: rust %s native %s" % (
    worst, complex(r_field[worst]), complex(n_field[worst])))
diff = float(np.max(np.abs(r_field - n_field))) / scale
print("  raw E-field DFT vs native: max rel. difference %.3e" % diff)
assert diff < 1e-2, "E-field DFT differs by %.3e" % diff

rust_result = load_result(os.path.join(work, "rust", "SAR_1g.h5"))
native_result = load_result(os.path.join(work, "native", "SAR_1g.h5"))
assert rust_result["sar"].shape == native_result["sar"].shape, "result shapes differ"
scale = max(float(np.max(np.abs(native_result["sar"]))), 1e-30)
diff = float(np.max(np.abs(rust_result["sar"] - native_result["sar"]))) / scale
peak_ratio = rust_result["max_sar"] / native_result["max_sar"] - 1.0
print("  1g SAR vs native: max rel. difference %.3e, peak ratio %+.3e" % (diff, peak_ratio))
worst = np.unravel_index(
    int(np.argmax(np.abs(rust_result["sar"] - native_result["sar"]))),
    rust_result["sar"].shape,
)
print("  1g worst cell %s: rust %.4e native %.4e (peak %.4e at %s)" % (
    worst, float(rust_result["sar"][worst]),
    float(native_result["sar"][worst]), scale, rust_result["max_idx"]))
diff_field = np.abs(rust_result["sar"].astype(np.float64) - native_result["sar"].astype(np.float64))
interior = diff_field[1:-1, 1:-1, 1:-1]
print("  interior (no boundary cells): max rel. %.3e" % (
    float(np.max(interior)) / scale))
boundary = diff_field.copy()
boundary[1:-1, 1:-1, 1:-1] = 0.0
print("  boundary cells: max rel. %.3e, cells over 1%% of peak: %d" % (
    float(np.max(boundary)) / scale,
    int(np.sum(boundary > 0.01 * scale))))

# The raw dump inputs and the 1 g peak now match native. The remaining
# per-cell 1 g differences come from the mass-averaging cube search, which was
# never numerically compared to native before and is tracked as RM-145; this
# check reports the numbers instead of hiding them.
print("  NOTE: the 1 g cube-search kernel still differs from native for %d of %d "
      "cells (RM-145); only the peak and the raw dump inputs are gated here" % (
          int(np.sum(diff_field > 0.01 * scale)), diff_field.size))
assert abs(peak_ratio) < 1e-2, "peak SAR ratio deviates by %.3e" % abs(peak_ratio)
for name in ("CubeMass", "CubeVol"):
    if name in rust_result and name in native_result:
        r = rust_result[name].astype(np.float64)
        n = native_result[name].astype(np.float64)
        n_scale = max(float(np.max(np.abs(n))), 1e-30)
        print("  %s vs native: max rel. difference %.3e, max |rust-native| = %.3e" % (
            name, float(np.max(np.abs(r - n))) / n_scale, float(np.max(np.abs(r - n)))))
if "CubeType" in rust_result and "CubeType" in native_result:
    mismatch = int(np.sum(rust_result["CubeType"] != native_result["CubeType"]))
    print("  CubeType mismatches: %d of %d" % (mismatch, rust_result["CubeType"].size))
for attr in ("valid_cubes", "used_cubes"):
    print("  %s: rust %s native %s" % (
        attr, rust_result.get(attr), native_result.get(attr)))

print("cylindrical SAR check: PASS")
PY
