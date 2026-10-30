#!/usr/bin/env python3
"""Mesh-refinement study for the canonical PEC cavity.

Runs the Rust engine through the Python bindings at h, h/2 and h/4, extracts the
TE101 resonance from a voltage probe, compares it with the analytic eigenmode
and reports the observed order. The script is a study, not a CI gate: it prints
a table and writes a JSON record.

Usage (WSL, inside the Rust venv):

    PYTHONPATH=openEMS/rust-py/python:CSXCAD/rust-py/python \
        ~/rustpy-venv/bin/python scripts/ci/convergence_study.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile

import numpy as np

from CSXCAD import ContinuousStructure
from openEMS import openEMS

C0 = 299_792_458.0
A = 5.0e-2
B = 2.0e-2
D = 6.0e-2
F_START = 1.0e9
F_STOP = 10.0e9


def analytic_te101() -> float:
    return C0 / 2.0 * math.sqrt((1.0 / A) ** 2 + (1.0 / D) ** 2)


def build_and_run(nx: int, ny: int, nz: int, steps: int) -> dict:
    x = np.linspace(0.0, A, nx)
    y = np.linspace(0.0, B, ny)
    z = np.linspace(0.0, D, nz)

    csx = ContinuousStructure()
    grid = csx.GetGrid()
    grid.SetDeltaUnit(1.0)
    grid.SetLines("x", x)
    grid.SetLines("y", y)
    grid.SetLines("z", z)

    excite = csx.AddExcitation("excite1", 0, [1, 1, 1])
    i, j, k = nx * 2 // 3, ny * 2 // 3, nz * 2 // 3
    excite.AddCurve(
        [[x[i], x[i + 1]], [y[j], y[j + 1]], [z[k], z[k + 1]]]
    )

    probe = csx.AddProbe("ut1y", 0)
    probe.AddBox(
        [x[nx // 4], y[ny // 2], z[nz // 5]],
        [x[nx // 4], y[ny // 2 + 1], z[nz // 5]],
    )

    fdtd = openEMS(NrTS=steps, EndCriteria=0)
    fdtd.SetGaussExcite((F_STOP - F_START) / 2.0, (F_STOP - F_START) / 2.0)
    fdtd.SetBoundaryCond(["PEC"] * 6)
    fdtd.SetCSX(csx)

    sim = tempfile.mkdtemp(prefix="openems-convergence-")
    fdtd.Run(sim, verbose=0)

    with open(os.path.join(sim, "ut1y"), encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    first = next(
        index
        for index, line in enumerate(lines)
        if line.strip() and not line.lstrip().startswith(("%", "#"))
    )
    data = np.loadtxt(lines[first:])
    raw_t = data[:, 0]
    raw_v = data[:, 1]
    # Native cavity test drops the excitation transient before the DFT.
    keep = raw_t >= 7.0e-10
    return {
        "mesh": [nx, ny, nz],
        "cells": nx * ny * nz,
        "steps": steps,
        "sample_interval": float(np.mean(np.diff(raw_t))),
        "duration": float(raw_t[-1] - raw_t[keep][0]),
        "t": raw_t[keep],
        "v": raw_v[keep],
    }


def peak_frequency(run: dict, window_s: float, samples: int) -> dict:
    """Resample to a common window and sample count, then find the TE101 peak."""
    t0 = float(run["t"][0])
    grid = t0 + np.linspace(0.0, window_s, samples, endpoint=False)
    values = np.interp(grid, run["t"], run["v"])
    window = np.hanning(len(values))
    nfft = 1 << int(math.ceil(math.log2(len(values) * 32)))
    spectrum = np.fft.rfft(values * window, nfft)
    freq = np.fft.rfftfreq(nfft, window_s / samples)
    magnitude = np.abs(spectrum)

    band = (freq > 3.0e9) & (freq < 5.0e9)
    index = int(np.argmax(np.where(band, magnitude, 0.0)))
    if 0 < index < len(magnitude) - 1:
        left = math.log(max(magnitude[index - 1], 1e-300))
        middle = math.log(max(magnitude[index], 1e-300))
        right = math.log(max(magnitude[index + 1], 1e-300))
        denominator = left - 2.0 * middle + right
        offset = 0.5 * (left - right) / denominator if denominator != 0.0 else 0.0
    else:
        offset = 0.0
    peak = float(freq[index] + offset * (freq[1] - freq[0]))
    return {
        "te101_hz": peak,
        "relative_error": abs(peak - analytic_te101()) / analytic_te101(),
        "window_s": window_s,
        "fft_bin_hz": 1.0 / window_s,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        default="docs/migration/reference-data/convergence/cavity.json",
    )
    args = parser.parse_args()
    # fdtd.Run() changes the process working directory; resolve now.
    args.json = os.path.abspath(args.json)

    # Longer runs than the first attempt so every level covers the same
    # physical window; the common window is then the shortest of them.
    levels = [(10, 5, 12, 8000), (20, 10, 24, 16000), (40, 20, 48, 32000)]
    runs = [build_and_run(*level) for level in levels]
    window_s = min(run["duration"] for run in runs)
    samples = 1 << 16

    rows = []
    for run in runs:
        peak = peak_frequency(run, window_s, samples)
        row = {
            "mesh": run["mesh"],
            "cells": run["cells"],
            "steps": run["steps"],
            "sample_interval": run["sample_interval"],
            **peak,
        }
        rows.append(row)
        print(
            "mesh {mesh[0]}x{mesh[1]}x{mesh[2]} ({cells} cells, {steps} steps): "
            "TE101 {te101_hz:.6e} Hz, rel err {relative_error:.3e}".format(**row)
        )

    exact = analytic_te101()
    print(f"analytic TE101: {exact:.6e} Hz (common window {window_s*1e9:.2f} ns)")
    errors = [row["relative_error"] for row in rows]
    orders = []
    for i in range(1, len(rows)):
        if errors[i] <= 0.0 or errors[i - 1] <= 0.0:
            orders.append(None)
            continue
        ratio = rows[i]["mesh"][0] / rows[i - 1]["mesh"][0]
        order = math.log(errors[i - 1] / errors[i]) / math.log(ratio)
        orders.append(order)
        print(f"observed order {rows[i-1]['mesh'][0]}->{rows[i]['mesh'][0]}: {order:.2f}")

    record = {
        "case": "PEC cavity, TE101",
        "geometry_m": [A, B, D],
        "analytic_hz": exact,
        "levels": rows,
        "observed_order": orders,
        "engine": "Rust openEMS Python bindings",
        "probe": "ut1y",
        "window": "common window, Hann, 32x zero-padding, quadratic peak interpolation",
        "samples": samples,
    }
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
