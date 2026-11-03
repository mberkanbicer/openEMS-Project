#!/usr/bin/env python3
"""Compare an openEMS MSL-notch sweep with a CST export (E-009 / CST-001).

The reference side is the converged Rust/native FDTD result recorded in
``docs/migration/reference-data/convergence/msl_notch.json`` (finest mesh,
notch at 3.6700 GHz). The CST side is a Touchstone file (``.s2p``) exported
from the model built by ``docs/migration/cst/msl_notch.bas``.

Acceptance gates (proposed with the first CST fixture, see the CST README):

* notch (|S11| maximum) within 1.0 % of the reference;
* |S11| at the notch >= 0.8 on both sides (the shunt stub reflects);
* |S21| at the notch <= -20 dB on both sides (the notch rejects);
* RMS of |S11| in dB over the common band, floored at -40 dB, <= 3 dB.

The script refuses to invent data: without a CST file it exits 2 and says so.
``--self-test`` exercises the parser and the gates on synthetic Touchstone
files, so the harness itself is verifiable without a CST installation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

REFERENCE = Path("docs/migration/reference-data/convergence/msl_notch.json")
UNIT_SCALE = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}


def parse_touchstone(text: str) -> list[tuple[float, complex, complex]]:
    """Return (frequency_hz, S11, S21) from a 2-port Touchstone file."""
    freq_unit = "GHZ"
    fmt = "MA"
    rows: list[tuple[float, complex, complex]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            tokens = line[1:].upper().split()
            for token in tokens:
                if token in UNIT_SCALE:
                    freq_unit = token
                elif token in ("RI", "MA", "DB"):
                    fmt = token
            continue
        values = []
        for token in line.split():
            try:
                values.append(float(token))
            except ValueError:
                raise ValueError(f"non-numeric Touchstone field: {token!r}")
        if len(values) < 9:
            raise ValueError(
                f"expected 9 fields for a 2-port row (f, S11, S21, S12, S22), got {len(values)}"
            )
        freq = values[0] * UNIT_SCALE[freq_unit]

        def pair(mag: float, phase: float) -> complex:
            if fmt == "RI":
                return complex(mag, phase)
            if fmt == "DB":
                mag = 10 ** (mag / 20.0)
            angle = math.radians(phase)
            return complex(mag * math.cos(angle), mag * math.sin(angle))

        s11 = pair(values[1], values[2])
        s21 = pair(values[3], values[4])
        rows.append((freq, s11, s21))
    if not rows:
        raise ValueError("no data rows in Touchstone file")
    rows.sort(key=lambda row: row[0])
    return rows


def load_reference(path: Path) -> tuple[list[float], list[float], list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    run = data["levels"][-1]
    freqs = [float(value) for value in data["frequencies_hz"]]
    if len(freqs) != len(run["s11_curve"]):
        raise ValueError("reference frequency and curve lengths differ")
    return freqs, run["s11_curve"], run["s21_curve"]


def interpolate(xs: Iterable[float], ys: Iterable[float], x: float) -> float:
    xs = list(xs)
    ys = list(ys)
    if not xs:
        raise ValueError("empty curve")
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    import bisect

    index = bisect.bisect_left(xs, x)
    if index < len(xs) and xs[index] == x:
        return ys[index]
    x0, x1 = xs[index - 1], xs[index]
    y0, y1 = ys[index - 1], ys[index]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def notch(curve: list[float], freqs: list[float]) -> tuple[float, float]:
    """Return (frequency, value) of the curve maximum with a parabolic fit."""
    index = max(range(len(curve)), key=lambda i: curve[i])
    if index == 0 or index == len(curve) - 1:
        return freqs[index], curve[index]
    y0, y1, y2 = curve[index - 1], curve[index], curve[index + 1]
    x0, x1, x2 = freqs[index - 1], freqs[index], freqs[index + 1]
    denom = (y0 - 2 * y1 + y2)
    if denom == 0:
        return x1, y1
    offset = 0.5 * (y0 - y2) / denom
    peak = y1 - 0.25 * (y0 - y2) * offset
    return x1 + offset * (x2 - x1), peak


def compare(
    reference: Path,
    cst_rows: list[tuple[float, complex, complex]],
    notch_rel_limit: float = 0.01,
    rms_limit_db: float = 3.0,
) -> dict:
    ref_freqs, ref_s11, ref_s21 = load_reference(reference)
    cst_freqs = [row[0] for row in cst_rows]
    cst_s11 = [abs(row[1]) for row in cst_rows]
    cst_s21 = [abs(row[2]) for row in cst_rows]

    ref_notch_hz, ref_notch_value = notch(ref_s11, ref_freqs)
    cst_notch_hz, cst_notch_value = notch(cst_s11, cst_freqs)
    notch_rel = abs(cst_notch_hz - ref_notch_hz) / ref_notch_hz

    ref_s21_notch = interpolate(ref_freqs, ref_s21, ref_notch_hz)
    cst_s21_notch = interpolate(cst_freqs, cst_s21, cst_notch_hz)

    low = max(ref_freqs[0], cst_freqs[0])
    high = min(ref_freqs[-1], cst_freqs[-1])
    if high <= low:
        raise ValueError("CST and reference bands do not overlap")
    count = 200
    diffs = []
    for step in range(count + 1):
        freq = low + (high - low) * step / count
        ref_db = 20 * math.log10(max(interpolate(ref_freqs, ref_s11, freq), 1e-3))
        cst_db = 20 * math.log10(max(interpolate(cst_freqs, cst_s11, freq), 1e-3))
        diffs.append((max(ref_db, -40.0) - max(cst_db, -40.0)) ** 2)
    rms_db = math.sqrt(sum(diffs) / len(diffs))

    gates = {
        "notch_frequency": notch_rel <= notch_rel_limit,
        "reflection_at_notch": ref_notch_value >= 0.8 and cst_notch_value >= 0.8,
        "rejection_at_notch": 20 * math.log10(max(ref_s21_notch, 1e-6)) <= -20.0
        and 20 * math.log10(max(cst_s21_notch, 1e-6)) <= -20.0,
        "shape_rms": rms_db <= rms_limit_db,
    }
    return {
        "reference_notch_hz": ref_notch_hz,
        "cst_notch_hz": cst_notch_hz,
        "notch_relative_difference": notch_rel,
        "reference_s11_at_notch": ref_notch_value,
        "cst_s11_at_notch": cst_notch_value,
        "reference_s21_at_notch_db": 20 * math.log10(max(ref_s21_notch, 1e-6)),
        "cst_s21_at_notch_db": 20 * math.log10(max(cst_s21_notch, 1e-6)),
        "s11_rms_db": rms_db,
        "band_hz": [low, high],
        "gates": gates,
        "passed": all(gates.values()),
    }


def write_report(result: dict, path: Path) -> None:
    lines = [
        "# CST cross-validation (E-009 / CST-001)",
        "",
        f"Notch reference: {result['reference_notch_hz'] / 1e9:.4f} GHz",
        f"Notch CST:       {result['cst_notch_hz'] / 1e9:.4f} GHz",
        f"Relative difference: {result['notch_relative_difference'] * 100:.3f} %",
        "",
        "| observable | reference | CST |",
        "| --- | --- | --- |",
        f"| \\|S11\\| at notch | {result['reference_s11_at_notch']:.4f} | {result['cst_s11_at_notch']:.4f} |",
        f"| \\|S21\\| at notch | {result['reference_s21_at_notch_db']:.2f} dB | {result['cst_s21_at_notch_db']:.2f} dB |",
        f"| \\|S11\\| RMS difference | - | {result['s11_rms_db']:.2f} dB |",
        "",
        f"Band: {result['band_hz'][0] / 1e9:.3f}-{result['band_hz'][1] / 1e9:.3f} GHz",
        "",
        "| gate | result |",
        "| --- | --- |",
    ]
    for name, passed in result["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.append("")
    lines.append("VERDICT: " + ("PASS" if result["passed"] else "FAIL"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test(reference: Path) -> int:
    ref_freqs, ref_s11, ref_s21 = load_reference(reference)
    failures = 0

    def touchstone(freqs: list[float], s11: list[float], s21: list[float], fmt: str) -> str:
        header = f"# GHZ S {fmt} R 50"
        rows = [header]
        for freq, a, b in zip(freqs, s11, s21):
            if fmt == "RI":
                rows.append(
                    f"{freq / 1e9:.9f} {a:.9f} 0.0 {b:.9f} 0.0 {b:.9f} 0.0 {a:.9f} 0.0"
                )
            else:
                rows.append(
                    f"{freq / 1e9:.9f} {a:.9f} 0.0 {b:.9f} 0.0 {b:.9f} 0.0 {a:.9f} 0.0"
                )
        return "\n".join(rows) + "\n"

    with tempfile.TemporaryDirectory() as tmp:
        # Same curve: must pass.
        same = Path(tmp) / "same.s2p"
        same.write_text(touchstone(ref_freqs, ref_s11, ref_s21, "RI"), encoding="utf-8")
        result = compare(reference, parse_touchstone(same.read_text(encoding="utf-8")))
        print("self-test identical:", result["passed"], f"rms={result['s11_rms_db']:.3f} dB")
        failures += 0 if result["passed"] else 1

        # 0.2 % notch shift with the same shape: must pass the 1 % gate.
        shifted = [f * 1.002 for f in ref_freqs]
        near = Path(tmp) / "near.s2p"
        near.write_text(touchstone(shifted, ref_s11, ref_s21, "RI"), encoding="utf-8")
        result = compare(reference, parse_touchstone(near.read_text(encoding="utf-8")))
        print(
            "self-test 0.2% shift:",
            result["passed"],
            f"notch={result['notch_relative_difference'] * 100:.3f}%",
        )
        failures += 0 if result["passed"] else 1

        # 3 % shift: must fail the gate.
        shifted = [f * 1.03 for f in ref_freqs]
        far = Path(tmp) / "far.s2p"
        far.write_text(touchstone(shifted, ref_s11, ref_s21, "RI"), encoding="utf-8")
        result = compare(reference, parse_touchstone(far.read_text(encoding="utf-8")))
        print(
            "self-test 3% shift:",
            not result["passed"],
            f"notch={result['notch_relative_difference'] * 100:.3f}%",
        )
        failures += 0 if not result["passed"] else 1

        # Magnitude/angle format must parse to the same curve.
        ma = Path(tmp) / "ma.s2p"
        ma.write_text(touchstone(ref_freqs, ref_s11, ref_s21, "MA"), encoding="utf-8")
        parsed = parse_touchstone(ma.read_text(encoding="utf-8"))
        same_curve = all(
            abs(abs(row[1]) - ref) < 1e-9 for row, ref in zip(parsed, ref_s11)
        )
        print("self-test MA format:", same_curve)
        failures += 0 if same_curve else 1

    print("self-test:", "PASS" if failures == 0 else f"FAIL ({failures})")
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cst", type=Path, help="CST Touchstone export (.s2p)")
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--out", type=Path, help="write a Markdown report here")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--notch-rel-limit", type=float, default=0.01)
    parser.add_argument("--rms-limit-db", type=float, default=3.0)
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.reference)
    if not args.cst:
        print(
            "CST data missing: pass --cst <export.s2p>; see docs/migration/cst/README.md",
            file=sys.stderr,
        )
        return 2
    if not args.cst.exists():
        print(f"CST data missing: {args.cst}", file=sys.stderr)
        return 2

    try:
        rows = parse_touchstone(args.cst.read_text(encoding="utf-8", errors="replace"))
        result = compare(args.reference, rows, args.notch_rel_limit, args.rms_limit_db)
    except (ValueError, KeyError, IndexError) as error:
        print(f"CST comparison failed to parse/compare: {error}", file=sys.stderr)
        return 1

    if args.out:
        write_report(result, args.out)
    print(json.dumps(result, indent=2))
    print("CST comparison:", "PASS" if result["passed"] else "FAIL")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
