#!/usr/bin/env bash
# RM-138 check: cylindrical field dumps.
#
# Mirrors the plain part of the native `openEMS/python/Tests/Cylindrical_Cavity.py`
# (PEC pillbox on a closed mesh with the rho = 0 axis) and adds an E-field
# frequency-domain dump. The Rust and native solvers run on the exact same
# `input.xml`; the HDF5 dump layout (/Mesh/rho,alpha,z), the dump field values
# and the TM010 radial Ez profile against J0 are compared.
#
# Usage: scripts/ci/run_cylindrical_dump_check_wsl.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi
export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"

WORK="${TMPDIR:-/tmp}/cyl_dump_check"
rm -rf "$WORK"
mkdir -p "$WORK/rust" "$WORK/native"

"$PYTHON" - "$WORK" <<'PY'
import os
import sys

import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

work = sys.argv[1]
unit = 1e-3          # drawing unit: mm
radius = 50.0        # cavity radius (mm)
height = 30.0        # cavity height (mm)
dr = dz = 2.5
n_alpha = 24

f_start = 1.5e9
f_stop = 4.5e9
x_01 = 2.404826      # first zero of J0
f_010 = x_01 * C0 / (2 * np.pi * radius * unit)

sim_path = os.path.join(work, "rust")
FDTD = openEMS(CoordSystem=1, NrTS=40000, EndCriteria=0)
FDTD.SetGaussExcite(0.5 * (f_start + f_stop), 0.5 * (f_stop - f_start))
FDTD.SetBoundaryCond(["PEC"] * 6)

CSX = ContinuousStructure(CoordSystem=1)
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(unit)
mesh.AddLine("r", np.arange(0, radius + dr / 2, dr))
mesh.AddLine("a", (np.arange(n_alpha + 1) - n_alpha / 2) * 2 * np.pi / n_alpha)
mesh.AddLine("z", np.arange(0, height + dz / 2, dz))

src = CSX.AddExcitation("line_source", exc_type=0, exc_val=[0, 0, 1])
src.AddBox([7 * dr, 0, 0], [7 * dr, 0, height])
CSX.AddProbe("et", p_type=2).AddPoint([10 * dr, np.pi / 4, height / 2])

dump = CSX.AddDump("Ef", dump_type=10, dump_mode=1, file_type=1, frequency=[f_010])
dump.AddBox([0, -np.pi, height / 2], [radius, np.pi, height / 2])

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


def bessel_j0(x):
    """J0(x) = 1/pi * int_0^pi cos(x sin(t)) dt (same scheme as the native test)"""
    t = np.linspace(0, np.pi, 2001)
    y = np.cos(np.outer(np.atleast_1d(x), np.sin(t)))
    return np.sum(0.5 * (y[:, 1:] + y[:, :-1]), axis=1) * (t[1] - t[0]) / np.pi


work = sys.argv[1]
f_010 = 2.404826 * 299792458.0 / (2 * np.pi * 50e-3)

def load(path):
    with h5py.File(path, "r") as handle:
        mesh_type = handle["/Mesh"].attrs["mesh_type"]
        mesh = {
            name: handle["/Mesh/" + name][()]
            for name in ("rho", "alpha", "z")
            if "/Mesh/" + name in handle
        }
        scaling = handle["/Mesh"].attrs["mesh_scaling"]
        datasets = [
            key for key in handle["/FieldData/FD"]
            if key.startswith("f")
        ]
        field = handle["/FieldData/FD/" + datasets[0]][()]
        frequency = handle["/FieldData/FD/" + datasets[0]].attrs.get("frequency")
    return mesh_type, scaling, mesh, field, frequency

rust = load(os.path.join(work, "rust", "Ef.h5"))
native = load(os.path.join(work, "native", "Ef.h5"))

for label, data in (("rust", rust), ("native", native)):
    mesh_type, scaling, mesh, field, frequency = data
    print("  %s: mesh_type=%s scaling=%s mesh=%s field=%s f=%s" % (
        label, mesh_type, scaling,
        {name: value.shape for name, value in mesh.items()},
        field.shape, frequency,
    ))

assert rust[0] == 1 and native[0] == 1, "both dumps must declare mesh_type 1"
for name in ("rho", "alpha", "z"):
    r, n = rust[2][name], native[2][name]
    assert r.shape == n.shape, "%s shape %s vs %s" % (name, r.shape, n.shape)
    scale = max(float(np.max(np.abs(n))), 1.0)
    diff = float(np.max(np.abs(r - n))) / scale
    print("  mesh %s: max rel. difference %.3e" % (name, diff))
    assert diff < 1e-9, "mesh %s differs by %.3e" % (name, diff)

r_field, n_field = rust[3], native[3]
assert r_field.shape == n_field.shape, "field shape %s vs %s" % (
    r_field.shape, n_field.shape)
scale = float(np.max(np.abs(n_field)))
assert scale > 0.0, "native dump is all zero"
diff = float(np.max(np.abs(r_field - n_field))) / scale
print("  dump field vs native: max rel. difference %.3e" % diff)
assert diff < 1e-2, "field differs from native by %.3e" % diff

# TM010 radial profile: alpha-averaged |Ez| against J0 (native test bound 0.03)
unit = 1e-3
r_lines = rust[2]["rho"] / unit
ez = np.abs(r_field[2, :, :, 0])
profile = np.mean(ez, axis=1)
profile /= profile[0]
expected = bessel_j0(2.404826 * r_lines / 50.0)
error = float(np.max(np.abs(profile - expected)))
print("  TM010 radial profile: max deviation from J0 = %.4f" % error)
assert error < 0.03, "radial profile deviates by %.4f" % error

print("cylindrical dump check: PASS")
PY
