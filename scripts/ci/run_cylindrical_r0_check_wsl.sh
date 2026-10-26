#!/usr/bin/env bash
# RM-137 check: a full closed cylindrical mesh that includes the rho = 0 axis.
#
# Mirrors the plain part of the native `openEMS/python/Tests/Cylindrical_Cavity.py`
# (PEC pillbox, TM010/TM110 resonances) and additionally compares the probe
# signal against the native solver on the very same input.xml.
#
# Usage: scripts/ci/run_cylindrical_r0_check_wsl.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="${RUSTPY_VENV:-$HOME/rustpy-venv}"
PYTHON="${VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi
export PYTHONPATH="$REPO_ROOT/openEMS/rust-py/python:$REPO_ROOT/CSXCAD/rust-py/python${PYTHONPATH:+:$PYTHONPATH}"

WORK="${TMPDIR:-/tmp}/cyl_r0_check"
rm -rf "$WORK"
mkdir -p "$WORK/rust" "$WORK/native"

"$PYTHON" - "$WORK" <<'PY'
import os
import sys

import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0
from openEMS.utilities import DFT_time2freq

work = sys.argv[1]
unit = 1e-3          # drawing unit: mm
radius = 50.0        # cavity radius (mm)
height = 30.0        # cavity height (mm)
dr = dz = 2.5
n_alpha = 24

f_start = 1.5e9
f_stop = 4.5e9
freq = np.linspace(f_start, f_stop, 3001)
x_01 = 2.404826      # first zero of J0
x_11 = 3.831706      # first zero of J1
f_010 = x_01 * C0 / (2 * np.pi * radius * unit)
f_110 = x_11 * C0 / (2 * np.pi * radius * unit)

sim_path = os.path.join(work, "rust")
FDTD = openEMS(CoordSystem=1, NrTS=40000, EndCriteria=0)
FDTD.SetGaussExcite(0.5 * (f_start + f_stop), 0.5 * (f_stop - f_start))
FDTD.SetBoundaryCond(["PEC"] * 6)   # r = 0 and the closed alpha need no BC

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

error = FDTD.Run(sim_path, cleanup=False)
if error != 0:
    raise SystemExit("rust run failed: %d" % error)
FDTD.Write2XML(os.path.join(sim_path, "input.xml"))

# analysis of the rust probe
data = np.loadtxt(os.path.join(sim_path, "et"), comments="%")
spec = np.abs(DFT_time2freq(data[:, 0], data[:, 3], freq))
results = {}
for mode, f_ana in (("TM010", f_010), ("TM110", f_110)):
    mask = np.abs(freq - f_ana) < 0.05 * f_ana
    peak = freq[mask][np.argmax(spec[mask])]
    results[mode] = peak
    print("  %s: %.4f GHz (analytic %.4f GHz), error %+.2f %%"
          % (mode, peak / 1e9, f_ana / 1e9, (peak / f_ana - 1) * 100))
    if abs(peak / f_ana - 1) >= 0.01:
        raise SystemExit("FAIL: %s off by more than 1 %%" % mode)
np.save(os.path.join(work, "rust_modes.npy"), np.array([results["TM010"], results["TM110"]]))
PY

# Native solver on the exact same input
cp "$WORK/rust/input.xml" "$WORK/native/input.xml"
( cd "$WORK/native" && "${NATIVE_OPENEMS:-$HOME/opt/openEMS/bin/openEMS}" input.xml > log 2>&1 )

"$PYTHON" - "$WORK" <<'PY'
import os
import sys

import numpy as np

from openEMS.physical_constants import C0
from openEMS.utilities import DFT_time2freq

work = sys.argv[1]
freq = np.linspace(1.5e9, 4.5e9, 3001)
f_010 = 2.404826 * C0 / (2 * np.pi * 50e-3)
f_110 = 3.831706 * C0 / (2 * np.pi * 50e-3)

rust = np.loadtxt(os.path.join(work, "rust", "et"), comments="%")
native = np.loadtxt(os.path.join(work, "native", "et"), comments="%")
if rust.shape != native.shape:
    raise SystemExit("FAIL: probe shapes differ %s vs %s" % (rust.shape, native.shape))
scale = max(float(np.max(np.abs(native[:, 1:]))), 1e-30)
difference = float(np.max(np.abs(rust[:, 1:] - native[:, 1:]))) / scale
print("  probe vs native: max rel. difference %.3e" % difference)
if difference > 1e-2:
    raise SystemExit("FAIL: probe differs from native by %.3e" % difference)

for label, data in (("native", native), ("rust", rust)):
    spec = np.abs(DFT_time2freq(data[:, 0], data[:, 3], freq))
    peaks = []
    for f_ana in (f_010, f_110):
        mask = np.abs(freq - f_ana) < 0.05 * f_ana
        peaks.append(freq[mask][np.argmax(spec[mask])])
    print("  %s modes: TM010 %.4f GHz, TM110 %.4f GHz"
          % (label, peaks[0] / 1e9, peaks[1] / 1e9))

print("cylindrical rho=0 check: PASS")
PY
