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


def build_and_run(
    nx: int, ny: int, nz: int, steps: int, time_step_factor: float = 1.0
) -> dict:
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
    if time_step_factor != 1.0:
        fdtd.SetTimeStepFactor(time_step_factor)
    fdtd.SetGaussExcite((F_STOP - F_START) / 2.0, (F_STOP - F_START) / 2.0)
    fdtd.SetBoundaryCond(["PEC"] * 6)
    fdtd.SetCSX(csx)

    sim = tempfile.mkdtemp(prefix="openems-convergence-")
    fdtd.Run(sim, verbose=0)
    solver_dt = float(fdtd.GetTimeStep())

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
        "time_step_factor": time_step_factor,
        "solver_dt": solver_dt,
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


def phase_frequency(run: dict, window_s: float) -> dict:
    """Frequency from the unwrapped phase of the band-passed analytic signal.

    An FFT peak is limited by the window (1/window_s ~ 2.5 MHz at 400 ns) even
    with interpolation. The TE101 line is narrow and long-lived, so the slope of
    its unwrapped phase gives a much finer estimate.
    """
    t0 = float(run["t"][0])
    samples = 1 << 18
    grid = t0 + np.linspace(0.0, window_s, samples, endpoint=False)
    values = np.interp(grid, run["t"], run["v"])
    values = values - values.mean()

    spectrum = np.fft.fft(values)
    freqs = np.fft.fftfreq(len(values), window_s / samples)
    target = analytic_te101()
    mask = (freqs > target - 0.25e9) & (freqs < target + 0.25e9)
    analytic = np.fft.ifft(np.where(mask, spectrum, 0.0)) * 2.0

    amplitude = np.abs(analytic)
    threshold = 0.2 * float(amplitude.max())
    keep = amplitude > threshold
    # Ignore the excitation transient and the low-amplitude tail.
    keep[: len(values) // 5] = False
    if int(keep.sum()) < 1000:
        raise SystemExit("phase estimator: too few samples above threshold")

    phase = np.unwrap(np.angle(analytic))
    slope = float(np.polyfit(grid[keep], phase[keep], 1)[0])
    peak = slope / (2.0 * math.pi)
    return {
        "te101_hz": peak,
        "relative_error": abs(peak - analytic_te101()) / analytic_te101(),
        "window_s": window_s,
        "fft_bin_hz": 1.0 / window_s,
        "phase_samples": int(keep.sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mesh", "dt"], default="mesh")
    parser.add_argument("--estimator", choices=["fft", "phase"], default=None)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()
    estimator = args.estimator or ("phase" if args.mode == "dt" else "fft")
    args.json = os.path.abspath(
        args.json
        or (
            "docs/migration/reference-data/convergence/cavity.json"
            if args.mode == "mesh"
            else "docs/migration/reference-data/convergence/cavity_dt.json"
        )
    )

    if args.mode == "mesh":
        levels = [(10, 5, 12, 8000), (20, 10, 24, 16000), (40, 20, 48, 32000)]
        runs = [build_and_run(*level) for level in levels]
        label = "PEC cavity, TE101, mesh refinement"
    else:
        # Fixed mesh; halve dt and double the step count to keep a 400 ns
        # window, which puts the raw FFT bin at 2.5 MHz and lets the phase
        # estimator resolve the temporal error.
        settings = [(1.0, 84000), (0.5, 168000), (0.25, 336000)]
        runs = [
            build_and_run(20, 10, 24, steps, factor)
            for factor, steps in settings
        ]
        label = "PEC cavity, TE101, time-step refinement"

    window_s = min(run["duration"] for run in runs)
    samples = 1 << 16
    estimate = phase_frequency if estimator == "phase" else lambda run, window: peak_frequency(run, window, samples)

    rows = []
    for run in runs:
        peak = estimate(run, window_s)
        row = {
            "mesh": run["mesh"],
            "cells": run["cells"],
            "steps": run["steps"],
            "time_step_factor": run["time_step_factor"],
            "solver_dt": run["solver_dt"],
            "sample_interval": run["sample_interval"],
            **peak,
        }
        rows.append(row)
        print(
            "mesh {mesh[0]}x{mesh[1]}x{mesh[2]} ({cells} cells, {steps} steps, "
            "dt factor {time_step_factor}): TE101 {te101_hz:.6e} Hz, "
            "rel err {relative_error:.3e}".format(**row)
        )


    exact = analytic_te101()
    print(f"analytic TE101: {exact:.6e} Hz (common window {window_s*1e9:.2f} ns)")
    orders = []
    if args.mode == "dt":
        # At fixed mesh the dt -> 0 limit is the finest time step, not the
        # analytic value: the remaining offset is the spatial error measured by
        # the mesh study. Refinement is judged against that limit.
        reference = rows[-1]["te101_hz"]
        for row in rows:
            row["difference_vs_finest_hz"] = row["te101_hz"] - reference
        diffs = [abs(row["difference_vs_finest_hz"]) for row in rows[:-1]]
        for i in range(len(diffs) - 1):
            if diffs[i] <= 0.0 or diffs[i + 1] <= 0.0:
                orders.append(None)
                continue
            order = math.log(diffs[i] / diffs[i + 1]) / math.log(2.0)
            orders.append(order)
            print(f"time-step order between factor steps {i + 1}: {order:.2f}")
        print(
            "fixed-mesh dt->0 limit: {:.6e} Hz; residual vs analytic {:.3e} Hz "
            "(spatial error)".format(reference, reference - exact)
        )
    else:
        errors = [row["relative_error"] for row in rows]
        for i in range(1, len(rows)):
            if errors[i] <= 0.0 or errors[i - 1] <= 0.0:
                orders.append(None)
                continue
            ratio = rows[i]["mesh"][0] / rows[i - 1]["mesh"][0]
            order = math.log(errors[i - 1] / errors[i]) / math.log(ratio)
            orders.append(order)
            print(f"observed order step {i}: {order:.2f}")

    record = {
        "case": label,
        "mode": args.mode,
        "estimator": estimator,
        "geometry_m": [A, B, D],
        "analytic_hz": exact,
        "levels": rows,
        "observed_order": orders,
        "reference": (
            "finest time step (factor 0.25) at fixed mesh" if args.mode == "dt" else "analytic"
        ),
        "note": (
            "self-convergence at fixed mesh: the dt->0 limit is the finest step; "
            "the residual against the analytic mode is the spatial error"
            if args.mode == "dt"
            else "mesh refinement supports the reported order"
        ),
        "engine": "Rust openEMS Python bindings",
        "probe": "ut1y",
        "window": (
            "common window, band-passed analytic signal, unwrapped-phase slope"
            if estimator == "phase"
            else "common window, Hann, 32x zero-padding, quadratic peak interpolation"
        ),
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
