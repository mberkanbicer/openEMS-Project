#!/usr/bin/env python3
"""Differential harness over the stored native reference data (RM-117/RM-118).

Each case runs the *unmodified* pinned source against the Rust openEMS core,
captures the solver outputs that the source normally deletes, and compares the
derived physical quantities against the native reference recorded in
``docs/migration/reference-data``.

Usage::

    python reference_harness.py --case coax [--keep]
    python reference_harness.py --case all

The comparison tolerances live in ``TOLERANCES`` and are justified in
``docs/migration/REFERENCE_TOLERANCES.md`` (RM-119). The script exits non-zero
if any case fails, so it can gate CI.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
import traceback

import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFERENCE_ROOT = os.path.join(REPO_ROOT, "docs", "migration", "reference-data")
TESTS = os.path.join(REPO_ROOT, "openEMS", "python", "Tests")
SMOKE = os.path.join(REPO_ROOT, "openEMS", ".github", "smoketests", "python")


# --------------------------------------------------------------------------
# Tolerances (RM-119). Every entry is a differential bound between two
# implementations of the same discretisation, not a physics acceptance limit.
# --------------------------------------------------------------------------
TOLERANCES = {
    # The staircase discretisation dominates Z_ref; two runs of the native
    # solver differ by < 1e-3 relative, so a 1 % bound leaves room for the
    # floating-point path difference without hiding a real regression.
    "coax_z_rel": 1.0e-2,
    # Transmission is smooth and lossless: the native run spread is 0.012 dB.
    "coax_s21_db": 5.0e-2,
    # S11 is a deep null (down to -50 dB); compare the worst return loss in
    # band with an absolute dB bound instead of a relative one.
    "coax_s11_db": 2.0,
    # Conducting-sheet transmission: the source test allows 0.25 dB / 10 deg;
    # the differential bound is tighter because the discretisation is shared.
    "sheet_mag_db": 2.0e-1,
    "sheet_phase_deg": 2.0,
    # Raw solver text outputs (port/probe samples): relative RMS over all rows.
    "text_rel_rms": 1.0e-2,
    # HDF5 field snapshots: relative RMS normalised by the peak magnitude.
    "hdf5_rel_rms": 1.0e-2,
}


def _reference(*parts: str) -> str:
    return os.path.join(REFERENCE_ROOT, *parts)


def _install_capture_hooks(capture_root: str) -> None:
    """Redirect tempfile and keep the solver output of the pinned sources."""
    os.makedirs(capture_root, exist_ok=True)
    tempfile.tempdir = capture_root

    import importlib

    oems_module = importlib.import_module("openEMS.openEMS")
    original_run = oems_module.openEMS.Run

    def keeping_run(self, sim_path, cleanup=False, **kwargs):
        # Keep the exact solver input next to the output for the audit trail.
        try:
            os.makedirs(str(sim_path), exist_ok=True)
            self.Write2XML(os.path.join(str(sim_path), "input.xml"))
        except Exception as error:  # pragma: no cover - diagnostics only
            print(f"  (could not write input.xml: {error})")
        return original_run(self, sim_path, cleanup=False, **kwargs)

    oems_module.openEMS.Run = keeping_run


def _run_source(path: str):
    import runpy

    return runpy.run_path(path, run_name="__main__")


def _text_columns(path: str) -> np.ndarray:
    return np.loadtxt(path, comments="%")


def _compare_text(actual_path: str, expected_path: str, label: str) -> tuple[bool, str]:
    actual = np.atleast_2d(_text_columns(actual_path))
    expected = np.atleast_2d(_text_columns(expected_path))
    if actual.shape != expected.shape:
        return False, f"{label}: shape {actual.shape} != reference {expected.shape}"
    scale = max(float(np.max(np.abs(expected))), 1.0e-30)
    difference = float(np.max(np.abs(actual - expected))) / scale
    ok = difference <= TOLERANCES["text_rel_rms"]
    return ok, f"{label}: max rel. difference {difference:.3e}"


def _compare_hdf5(actual_path: str, expected_path: str, label: str) -> tuple[bool, str]:
    import h5py

    worst = 0.0
    worst_name = ""
    with h5py.File(actual_path, "r") as actual, h5py.File(expected_path, "r") as expected:
        # A multi-timestep dump has near-zero late snapshots; normalising per
        # dataset would turn float noise into a "difference". Compare against
        # the peak of the whole file instead.
        global_scale = 0.0

        def collect(name, node):
            nonlocal global_scale
            if isinstance(node, h5py.Dataset) and np.issubdtype(node.dtype, np.number):
                global_scale = max(global_scale, float(np.max(np.abs(node[()]))))

        expected.visititems(collect)
        global_scale = max(global_scale, 1.0e-30)

        def visit(name, node):
            nonlocal worst, worst_name
            if not isinstance(node, h5py.Dataset):
                return
            if name not in expected:
                raise AssertionError(f"{label}: dataset {name} missing in reference")
            reference = expected[name][()]
            if node.shape != reference.shape:
                raise AssertionError(
                    f"{label}: {name} shape {node.shape} != {reference.shape}"
                )
            if not np.issubdtype(node.dtype, np.number):
                return
            left = np.asarray(node[()], dtype=np.float64)
            right = np.asarray(reference, dtype=np.float64)
            difference = float(np.max(np.abs(left - right))) / global_scale
            if difference > worst:
                worst = difference
                worst_name = name

        actual.visititems(visit)

    ok = worst <= TOLERANCES["hdf5_rel_rms"]
    return ok, f"{label}: worst dataset {worst_name or '-'} {worst:.3e}"


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------
def case_coax(capture_root: str) -> list[tuple[bool, str]]:
    results = []
    _install_capture_hooks(capture_root)
    namespace = _run_source(os.path.join(TESTS, "Coax.py"))

    reference = np.load(_reference("coax-3d-wsl", "run1-ports.npz"))
    freq = np.asarray(namespace["freq"])
    ports = namespace["ports"]
    s21 = np.asarray(namespace["s21"])
    s11 = np.asarray(namespace["s11"])

    mask = freq > 100e6
    reference_mask = np.asarray(reference["freq"]) > 100e6

    z_actual = np.real(ports[0].Z_ref[mask])
    z_reference = np.real(reference["p1_z_ref"][reference_mask])
    rel = float(np.max(np.abs(z_actual - z_reference) / np.abs(z_reference)))
    results.append(
        (
            rel <= TOLERANCES["coax_z_rel"],
            f"Z_ref (real): max rel. difference {rel:.3e}",
        )
    )

    s21_actual = 20 * np.log10(np.abs(s21[mask]))
    s21_reference = np.asarray(reference["s21_dB"])[reference_mask]
    delta = float(np.max(np.abs(s21_actual - s21_reference)))
    results.append(
        (delta <= TOLERANCES["coax_s21_db"], f"S21: max |delta| {delta:.3e} dB")
    )

    s11_actual = float(np.max(20 * np.log10(np.abs(s11[mask]))))
    s11_reference = float(np.max(np.asarray(reference["s11_dB"])[reference_mask]))
    delta = abs(s11_actual - s11_reference)
    results.append(
        (
            delta <= TOLERANCES["coax_s11_db"],
            f"S11 worst return loss: {s11_actual:.2f} dB vs {s11_reference:.2f} dB (delta {delta:.2f} dB)",
        )
    )
    return results


def case_conducting_sheet(capture_root: str) -> list[tuple[bool, str]]:
    _install_capture_hooks(capture_root)
    namespace = _run_source(os.path.join(TESTS, "Conducting_Sheet.py"))

    reference = np.load(_reference("conducting-sheet-wsl", "conducting-sheet-results.npz"))
    keys = {
        "Resistive film": "resistive_film",
        "Thin copper": "thin_copper",
        "Thick copper": "thick_copper",
    }
    results = []
    for name, prefix in keys.items():
        transmission, _ = namespace["results"][name]
        actual_db = 20 * np.log10(np.abs(transmission))
        expected_db = 20 * np.log10(np.abs(reference[prefix + "_T_fdtd"]))
        magnitude = float(np.max(np.abs(actual_db - expected_db)))
        results.append(
            (
                magnitude <= TOLERANCES["sheet_mag_db"],
                f"{name}: max |dB| difference {magnitude:.3f} dB",
            )
        )
        phase = np.angle(transmission, deg=True)
        expected_phase = np.angle(reference[prefix + "_T_fdtd"], deg=True)
        difference = float(np.max(np.abs(np.angle(np.exp(1j * np.deg2rad(phase - expected_phase)), deg=True))))
        results.append(
            (
                difference <= TOLERANCES["sheet_phase_deg"],
                f"{name}: max phase difference {difference:.3f} deg",
            )
        )
    return results


def _extract_tarball(path: str, target: str) -> None:
    os.makedirs(target, exist_ok=True)
    with tarfile.open(path, "r:gz") as archive:
        archive.extractall(target)


def case_fieldprobes(capture_root: str) -> list[tuple[bool, str]]:
    _install_capture_hooks(capture_root)
    namespace = _run_source(os.path.join(TESTS, "FieldProbes.py"))
    simulation_path = namespace["Sim_Path"]

    extracted = os.path.join(capture_root, "reference")
    if not os.path.isdir(extracted):
        _extract_tarball(_reference("fieldprobes-wsl", "fieldprobes-selected.tar.gz"), extracted)

    results = []
    for root, _dirs, files in os.walk(extracted):
        for name in sorted(files):
            expected_path = os.path.join(root, name)
            actual_path = os.path.join(simulation_path, name)
            if not os.path.isfile(actual_path):
                results.append((False, f"{name}: missing from the Rust run"))
                continue
            if name.endswith(".h5"):
                results.append(_compare_hdf5(actual_path, expected_path, name))
            else:
                results.append(_compare_text(actual_path, expected_path, name))
    return results


def case_msl_notchfilter(capture_root: str) -> list[tuple[bool, str]]:
    _install_capture_hooks(capture_root)
    namespace = _run_source(os.path.join(SMOKE, "MSL_NotchFilter.py"))
    simulation_path = namespace["Sim_Path"]

    reference_dir = _reference("msl-notchfilter-wsl", "run-1")
    results = []
    for name in sorted(os.listdir(reference_dir)):
        expected_path = os.path.join(reference_dir, name)
        if not os.path.isfile(expected_path):
            continue
        actual_path = os.path.join(simulation_path, name)
        if not os.path.isfile(actual_path):
            results.append((False, f"{name}: missing from the Rust run"))
            continue
        results.append(_compare_text(actual_path, expected_path, name))
    return results


CASES = {
    "coax": case_coax,
    "conducting-sheet": case_conducting_sheet,
    "fieldprobes": case_fieldprobes,
    "msl-notchfilter": case_msl_notchfilter,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="all", choices=["all", *CASES])
    parser.add_argument("--capture", default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    cases = list(CASES) if args.case == "all" else [args.case]
    root = args.capture or os.path.join(tempfile.gettempdir(), "openems-reference-harness")

    report = {}
    failed = False
    for name in cases:
        capture_root = os.path.join(root, name)
        if os.path.isdir(capture_root):
            shutil.rmtree(capture_root)
        os.makedirs(capture_root, exist_ok=True)
        print(f"\n=== {name} ===", flush=True)
        try:
            results = CASES[name](capture_root)
        except Exception:
            traceback.print_exc()
            results = [(False, "case raised an exception")]
        case_ok = all(ok for ok, _ in results)
        failed |= not case_ok
        report[name] = {
            "ok": case_ok,
            "checks": [{"ok": ok, "detail": detail} for ok, detail in results],
        }
        for ok, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {detail}")
        print(f"  ==> {name}: {'PASS' if case_ok else 'FAIL'}")
        if not args.keep:
            pass  # the capture root lives under the temp directory

    print("\n" + json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
