#!/usr/bin/env python3
"""Analytic SAR validation on a homogeneous lossy line.

A TEM line (PEC plates at z, PMC walls at y, PML at the x ends) is filled with
a homogeneous lossy dielectric. A 2 GHz Gaussian sheet source launches a plane
wave whose exact phasor is

    E(x) = E0 * exp(-(alpha + j beta) x)

with the analytic lossy-medium constants

    alpha, beta = omega * sqrt(mu eps / 2) * sqrt(sqrt(1 + (sigma/omega eps)^2) -+ 1)

The local SAR is ``0.5 * sigma * |E|^2 / rho``, so it must decay as
``exp(-2 alpha x)``. The check fits the simulated complex field and the SAR
output over 50-200 mm and compares the measured alpha, beta and SAR slope with
the closed-form values. This is the analytic SAR case that VAL-002 recorded as
missing; it does not rely on a native reference.

Run (WSL, Rust venv):
    PYTHONPATH=openEMS/rust-py/python:CSXCAD/rust-py/python \
        ~/rustpy-venv/bin/python scripts/ci/analytic_sar_check.py
"""

from __future__ import annotations

import json
import math
import os
import tempfile

import h5py
import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS

C0 = 299_792_458.0
EPS0 = 8.854_187_812_8e-12
MU0 = 1.256_637_062_12e-6

F0 = 2.0e9
ER = 4.0
SIGMA = 0.1
RHO = 1000.0
UNIT = 1e-3
DX = 0.5
X1 = 300.0
Y1 = Z1 = 5.0
X_SOURCE = 20.0
FIT_START = 50.0
FIT_STOP = 200.0
TOLERANCE = 2.0e-2


def analytic_constants() -> tuple[float, float]:
    omega = 2.0 * math.pi * F0
    eps = EPS0 * ER
    tangent = SIGMA / (omega * eps)
    root = math.sqrt(1.0 + tangent * tangent)
    scale = omega * math.sqrt(MU0 * eps / 2.0)
    return scale * math.sqrt(root - 1.0), scale * math.sqrt(root + 1.0)


def run_model(sim: str) -> None:
    csx = ContinuousStructure()
    mesh = csx.GetGrid()
    mesh.SetDeltaUnit(UNIT)
    mesh.AddLine("x", np.arange(0.0, X1 + DX / 2, DX))
    mesh.AddLine("y", np.arange(0.0, Y1 + DX / 2, DX))
    mesh.AddLine("z", np.arange(0.0, Z1 + DX / 2, DX))

    material = csx.AddMaterial("lossy", epsilon=ER, kappa=SIGMA, density=RHO)
    material.AddBox([-5, -1, -1], [X1 + 5, Y1 + 1, Z1 + 1])

    excite = csx.AddExcitation("ex", 0, [0, 0, 1])
    excite.AddBox([X_SOURCE, 0.0, 0.0], [X_SOURCE, Y1, Z1])

    raw = csx.AddDump("sar_raw", dump_type=29, dump_mode=2, file_type=1,
                      frequency=[F0])
    raw.AddBox([45.0, 0.0, 0.0], [210.0, Y1, Z1])
    local = csx.AddDump("sar", dump_type=20, dump_mode=2, file_type=1,
                        frequency=[F0])
    local.AddBox([45.0, 0.0, 0.0], [210.0, Y1, Z1])

    fdtd = openEMS(NrTS=20000, EndCriteria=1e-5)
    fdtd.SetGaussExcite(F0, 1.0e9)
    fdtd.SetBoundaryCond(["PML_8", "PML_8", "PMC", "PMC", "PEC", "PEC"])
    fdtd.SetCSX(csx)
    fdtd.Run(sim, verbose=0)


def fit(path: str, dataset: str, component: int | None) -> dict:
    with h5py.File(path, "r") as handle:
        field = handle[dataset][:]
        mesh_x = np.asarray(handle["Mesh/x"][:], dtype=float)
        density = handle["CellData/Density"][:] if "CellData" in handle else None
        conductivity = (
            handle["CellData/Conductivity"][:] if "CellData" in handle else None
        )
    centres = np.asarray(mesh_x, dtype=float)
    # The writer stores metres for these dumps; older/other layouts store
    # drawing units. Detect from the magnitude instead of guessing.
    if centres.size and abs(centres[-1]) > 1.0:
        centres = centres * UNIT
    mask = (centres >= FIT_START * UNIT) & (centres <= FIT_STOP * UNIT)
    x = centres[mask]
    if component is None:
        nx, ny, nz = field.shape
        mid_y, mid_z = ny // 2, nz // 2
        values = field[mask, mid_y, mid_z]
    else:
        _, nx, ny, nz = field.shape
        mid_y, mid_z = ny // 2, nz // 2
        values = field[component, mask, mid_y, mid_z]
    return {
        "x": x,
        "values": values,
        "density": density,
        "conductivity": conductivity,
        "mid_y": mid_y,
        "mid_z": mid_z,
        "shape": (nx, ny, nz),
    }


def main() -> int:
    alpha, beta = analytic_constants()
    sim = tempfile.mkdtemp(prefix="openems-analytic-sar-")
    run_model(sim)

    raw = fit(os.path.join(sim, "sar_raw.h5"), "FieldData/FD/f0", 2)
    local = fit(os.path.join(sim, "sar.h5"), "FieldData/FD/f0", None)

    magnitude = np.abs(raw["values"])
    phase = np.unwrap(np.angle(raw["values"]))
    if np.any(magnitude <= 0.0):
        raise SystemExit("analytic SAR: zero field sample inside the fit window")
    alpha_measured = -float(np.polyfit(raw["x"], np.log(magnitude), 1)[0])
    beta_measured = -float(np.polyfit(raw["x"], phase, 1)[0])

    sar = np.abs(local["values"])
    if np.any(sar <= 0.0):
        raise SystemExit("analytic SAR: zero SAR sample inside the fit window")
    sar_slope = -float(np.polyfit(local["x"], np.log(sar), 1)[0])

    # The SAR output must also equal sigma |E|^2 / (2 rho) point by point.
    # Both dumps share the physical mesh, so interpolate onto the same x.
    if raw["x"].shape == local["x"].shape and np.allclose(raw["x"], local["x"]):
        magnitude_common = magnitude
        sar_common = sar
    else:
        magnitude_common = np.interp(local["x"], raw["x"], magnitude)
        sar_common = sar
    sigma = float(raw["conductivity"][0, raw["mid_y"], raw["mid_z"]])
    density = float(raw["density"][0, raw["mid_y"], raw["mid_z"]])
    expected = 0.5 * sigma * magnitude_common**2 / density
    scale = float(np.max(expected))
    formula_error = float(np.max(np.abs(sar_common - expected))) / scale

    alpha_error = abs(alpha_measured - alpha) / alpha
    beta_error = abs(beta_measured - beta) / beta
    sar_error = abs(sar_slope - 2.0 * alpha) / (2.0 * alpha)

    print(
        f"analytic alpha {alpha:.6f} Np/m, beta {beta:.6f} rad/m; "
        f"measured alpha {alpha_measured:.6f} (rel {alpha_error:.3e}), "
        f"beta {beta_measured:.6f} (rel {beta_error:.3e})"
    )
    print(
        f"SAR slope {sar_slope:.6f} 1/m vs 2*alpha {2.0 * alpha:.6f} "
        f"(rel {sar_error:.3e}); SAR = sigma|E|^2/(2 rho) max deviation "
        f"{formula_error:.3e}"
    )

    ok = (
        alpha_error < TOLERANCE
        and beta_error < TOLERANCE
        and sar_error < TOLERANCE
        and formula_error < 1.0e-5
    )
    record = {
        "case": "homogeneous lossy TEM line, 2 GHz",
        "analytic": {
            "alpha_np_per_m": alpha,
            "beta_rad_per_m": beta,
            "epsilon_r": ER,
            "sigma_s_per_m": SIGMA,
            "density_kg_per_m3": RHO,
        },
        "measured": {
            "alpha_np_per_m": alpha_measured,
            "beta_rad_per_m": beta_measured,
            "sar_slope_per_m": sar_slope,
        },
        "relative_error": {
            "alpha": alpha_error,
            "beta": beta_error,
            "sar_slope": sar_error,
            "sar_formula": formula_error,
        },
        "tolerance": TOLERANCE,
        "fit_window_mm": [FIT_START, FIT_STOP],
        "result": "PASS" if ok else "FAIL",
        "command": "scripts/ci/run_analytic_sar_check_wsl.sh",
    }
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "migration",
        "reference-data",
        "convergence",
        "analytic_sar.json",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"wrote {path}")
    print("analytic SAR check: PASS" if ok else "analytic SAR check: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
