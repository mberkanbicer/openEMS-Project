#!/usr/bin/env python3
"""Mesh-refinement study for the microstrip notch filter.

Reuses the pinned smoke model (`openEMS/.github/smoketests/python/
MSL_NotchFilter.py`) with a longer record and three mesh resolutions. The
observable is the S11 notch (minimum |S11| in 3-7 GHz); the finest mesh is the
reference for the difference, so this is a self-convergence study, not an
analytic proof.

Run (WSL, Rust venv):
    PYTHONPATH=openEMS/rust-py/python:CSXCAD/rust-py/python \
        ~/rustpy-venv/bin/python scripts/ci/msl_convergence.py
"""

from __future__ import annotations

import json
import math
import os
import tempfile

import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

UNIT = 1e-6
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MSL_LENGTH = 50_000
MSL_WIDTH = 600
SUBSTRATE_THICKNESS = 254
SUBSTRATE_EPR = 3.66
STUB_LENGTH = 12e3
F_MAX = 7e9
STEPS = 30_000


def run_level(divisor: int) -> dict:
    sim = tempfile.mkdtemp(prefix=f"msl-notch-{divisor}-")
    resolution = C0 / (F_MAX * math.sqrt(SUBSTRATE_EPR)) / UNIT / divisor
    third_mesh = np.array([2 * resolution / 3, -resolution / 3]) / 4

    csx = ContinuousStructure()
    fdtd = openEMS(NrTS=STEPS)
    fdtd.SetGaussExcite(F_MAX / 2, F_MAX / 2)
    fdtd.SetBoundaryCond(["PML_8", "PML_8", "MUR", "MUR", "PEC", "MUR"])
    fdtd.SetCSX(csx)
    mesh = csx.GetGrid()
    mesh.SetDeltaUnit(UNIT)

    mesh.AddLine("x", 0)
    mesh.AddLine("x", MSL_WIDTH / 2 + third_mesh)
    mesh.AddLine("x", -MSL_WIDTH / 2 - third_mesh)
    mesh.SmoothMeshLines("x", resolution / 4)
    mesh.AddLine("x", [-MSL_LENGTH, MSL_LENGTH])
    mesh.SmoothMeshLines("x", resolution)

    mesh.AddLine("y", 0)
    mesh.AddLine("y", MSL_WIDTH / 2 + third_mesh)
    mesh.AddLine("y", -MSL_WIDTH / 2 - third_mesh)
    mesh.SmoothMeshLines("y", resolution / 4)
    mesh.AddLine("y", [-15 * MSL_WIDTH, 15 * MSL_WIDTH + STUB_LENGTH])
    mesh.AddLine("y", (MSL_WIDTH / 2 + STUB_LENGTH) + third_mesh)
    mesh.SmoothMeshLines("y", resolution)

    mesh.AddLine("z", np.linspace(0, SUBSTRATE_THICKNESS, 5))
    mesh.AddLine("z", 3000)
    mesh.SmoothMeshLines("z", resolution)

    substrate = csx.AddMaterial("RO4350B", epsilon=SUBSTRATE_EPR)
    substrate.AddBox(
        [-MSL_LENGTH, -15 * MSL_WIDTH, 0],
        [MSL_LENGTH, 15 * MSL_WIDTH + STUB_LENGTH, SUBSTRATE_THICKNESS],
    )

    pec = csx.AddMetal("PEC")
    port0 = fdtd.AddMSLPort(
        1,
        pec,
        [-MSL_LENGTH, -MSL_WIDTH / 2, SUBSTRATE_THICKNESS],
        [0, MSL_WIDTH / 2, 0],
        "x",
        "z",
        excite=-1,
        FeedShift=10 * resolution,
        MeasPlaneShift=MSL_LENGTH / 3,
        priority=10,
    )
    port1 = fdtd.AddMSLPort(
        2,
        pec,
        [MSL_LENGTH, -MSL_WIDTH / 2, SUBSTRATE_THICKNESS],
        [0, MSL_WIDTH / 2, 0],
        "x",
        "z",
        MeasPlaneShift=MSL_LENGTH / 3,
        priority=10,
    )
    pec.AddBox(
        [-MSL_WIDTH / 2, MSL_WIDTH / 2, SUBSTRATE_THICKNESS],
        [MSL_WIDTH / 2, MSL_WIDTH / 2 + STUB_LENGTH, SUBSTRATE_THICKNESS],
        priority=10,
    )

    fdtd.Run(sim, cleanup=True, verbose=0)

    freq = np.linspace(1e9, 7e9, 601)
    for port in (port0, port1):
        port.CalcPort(sim, freq, ref_impedance=50)
    s11 = np.abs(port0.uf_ref / port0.uf_inc)
    # Prefer an interior local minimum; a band-edge minimum is a roll-off, not a
    # notch. Keep the whole curve so the choice is auditable.
    interior = np.where(
        (s11[1:-1] < s11[:-2]) & (s11[1:-1] < s11[2:])
    )[0] + 1
    interior = interior[(freq[interior] > 1.2e9) & (freq[interior] < 6.8e9)]
    if len(interior):
        index = int(interior[np.argmin(s11[interior])])
        kind = "local minimum"
    else:
        index = int(np.argmin(s11))
        kind = "band-edge minimum (no interior notch)"
    notch = float(freq[index])
    depth = float(s11[index])
    print(
        f"divisor {divisor}: resolution {resolution:.4f} um, {kind} at "
        f"{notch/1e9:.4f} GHz, |S11| {depth:.4f}"
    )
    return {
        "divisor": divisor,
        "resolution_um": resolution,
        "notch_hz": notch,
        "s11_depth": depth,
        "minimum_kind": kind,
        "s11_curve": [float(value) for value in s11],
    }


def main() -> int:
    levels = [run_level(divisor) for divisor in (40, 50, 60)]
    reference = levels[-1]["notch_hz"]
    for level in levels:
        level["difference_hz"] = level["notch_hz"] - reference
        level["difference_rel"] = abs(level["notch_hz"] - reference) / reference
        print(
            f"divisor {level['divisor']}: difference vs finest "
            f"{level['difference_hz']/1e6:.3f} MHz ({level['difference_rel']:.3e})"
        )

    record = {
        "case": "microstrip notch filter, S11 notch",
        "model": "openEMS/.github/smoketests/python/MSL_NotchFilter.py",
        "steps": STEPS,
        "frequencies_hz": [float(value) for value in np.linspace(1e9, 7e9, 601)],
        "levels": levels,
        "reference": "finest mesh",
        "note": "self-convergence of a graded 3-D model; no analytic notch oracle",
    }
    path = os.path.join(
        REPO_ROOT, "docs", "migration", "reference-data", "convergence", "msl_notch.json"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
