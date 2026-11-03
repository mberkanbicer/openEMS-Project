#!/usr/bin/env python3
"""Scientific parity figures: native stack vs Rust port on identical inputs.

Runs the unmodified Python reference cases against the Rust packages, loads the
recorded native captures, and writes overlaid figures to
``docs/migration/audits/figures/``. Also runs both ``nf2ff`` binaries on the
same near-field dumps, and both solvers on the lossy guide.

Usage (from the repository root, with the Rust Python packages on PYTHONPATH):

    PYTHONPATH=openEMS/rust-py/python:CSXCAD/rust-py/python \
        python3 scripts/ci/plot_scientific_parity.py
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG_DIR = os.path.join(REPO_ROOT, "docs", "migration", "audits", "figures")
REFERENCE = os.path.join(REPO_ROOT, "docs", "migration", "reference-data")
TESTS = os.path.join(REPO_ROOT, "openEMS", "python", "Tests")
SMOKE = os.path.join(REPO_ROOT, "openEMS", ".github", "smoketests", "python")
NATIVE = os.path.expanduser("~/openems-exact/bin/openEMS")
RUST = os.path.join(REPO_ROOT, "target", "release", "openems-cli")


def load_harness():
    path = os.path.join(REPO_ROOT, "scripts", "ci", "reference_harness.py")
    spec = importlib.util.spec_from_file_location("reference_harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def figure_coax(harness):
    tempfile.tempdir = None
    work = tempfile.mkdtemp(prefix="parity-coax-")
    try:
        harness._install_capture_hooks(work)
        namespace = harness._run_source(os.path.join(TESTS, "Coax.py"))
        freq = np.asarray(namespace["freq"])
        s11 = np.asarray(namespace["s11"])
        s21 = np.asarray(namespace["s21"])
        z_ref = np.real(namespace["ports"][0].Z_ref)
        reference = np.load(os.path.join(REFERENCE, "coax-3d-wsl", "run1-ports.npz"))
        ref_freq = np.asarray(reference["freq"])
        mask = freq > 100e6
        ref_mask = ref_freq > 100e6
        f = freq[mask] / 1e9
        ref_f = ref_freq[ref_mask] / 1e9
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
        axes[0].plot(ref_f, np.real(reference["p1_z_ref"])[ref_mask], label="native", lw=2)
        axes[0].plot(f, z_ref[mask], "--", label="Rust", lw=1.4)
        axes[0].set_xlabel("frequency / GHz")
        axes[0].set_ylabel("Re(Z_ref) / Ohm")
        axes[0].set_title("Coax port impedance")
        axes[1].plot(ref_f, reference["s21_dB"][ref_mask], label="native", lw=2)
        axes[1].plot(f, 20 * np.log10(np.abs(s21[mask])), "--", label="Rust", lw=1.4)
        axes[1].set_xlabel("frequency / GHz")
        axes[1].set_ylabel("S21 / dB")
        axes[1].set_title("Coax transmission")
        axes[2].plot(ref_f, reference["s11_dB"][ref_mask], label="native", lw=2)
        axes[2].plot(f, 20 * np.log10(np.abs(s11[mask])), "--", label="Rust", lw=1.4)
        axes[2].set_xlabel("frequency / GHz")
        axes[2].set_ylabel("S11 / dB")
        axes[2].set_title("Coax reflection")
        for axis in axes:
            axis.grid(True, alpha=0.3)
            axis.legend()
        z_error = np.max(np.abs(z_ref[mask] - np.real(reference["p1_z_ref"])[ref_mask])
                         / np.abs(np.real(reference["p1_z_ref"])[ref_mask]))
        s21_error = np.max(np.abs(20 * np.log10(np.abs(s21[mask])) - reference["s21_dB"][ref_mask]))
        fig.suptitle(f"native vs Rust, identical Coax.py: Z error {z_error:.2e}, S21 error {s21_error:.2e} dB")
        fig.tight_layout()
        path = os.path.join(FIG_DIR, "coax-parity.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return z_error, s21_error
    finally:
        shutil.rmtree(work, ignore_errors=True)
        tempfile.tempdir = None


def figure_conducting_sheet(harness):
    tempfile.tempdir = None
    work = tempfile.mkdtemp(prefix="parity-sheet-")
    try:
        harness._install_capture_hooks(work)
        namespace = harness._run_source(os.path.join(TESTS, "Conducting_Sheet.py"))
        results = namespace["results"]
        reference = np.load(os.path.join(REFERENCE, "conducting-sheet-wsl", "conducting-sheet-results.npz"))
        freq = np.asarray(reference["frequency_Hz"]) / 1e9
        names = {"Resistive film": "resistive_film", "Thin copper": "thin_copper", "Thick copper": "thick_copper"}
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        worst = 0.0
        for label, prefix in names.items():
            transmission = np.asarray(results[label][0])
            native = reference[prefix + "_T_fdtd"]
            axes[0].plot(freq, 20 * np.log10(np.abs(native)), lw=2, label=f"native {label}")
            axes[0].plot(freq, 20 * np.log10(np.abs(transmission)), "--", lw=1.2, label=f"Rust {label}")
            axes[1].plot(freq, np.angle(native, deg=True), lw=2, label=f"native {label}")
            axes[1].plot(freq, np.angle(transmission, deg=True), "--", lw=1.2, label=f"Rust {label}")
            worst = max(worst, float(np.max(np.abs(20 * np.log10(np.abs(transmission)) - 20 * np.log10(np.abs(native))))))
        axes[0].set_xlabel("frequency / GHz")
        axes[0].set_ylabel("|T| / dB")
        axes[0].set_title("Conducting sheet transmission")
        axes[1].set_xlabel("frequency / GHz")
        axes[1].set_ylabel("phase / deg")
        axes[1].set_title("Conducting sheet phase")
        for axis in axes:
            axis.grid(True, alpha=0.3)
            axis.legend(fontsize=7)
        fig.suptitle(f"native vs Rust, identical Conducting_Sheet.py: worst |T| difference {worst:.3f} dB")
        fig.tight_layout()
        fig.savefig(os.path.join(FIG_DIR, "conducting-sheet-parity.png"), dpi=150)
        plt.close(fig)
        return worst
    finally:
        shutil.rmtree(work, ignore_errors=True)
        tempfile.tempdir = None


def figure_nf2ff():
    dump = os.path.join(REPO_ROOT, "openEMS", "TESTSUITE", "combinedtests", "tmp_nf2ff_dipole")
    if not os.path.isdir(dump):
        return None
    work = tempfile.mkdtemp(prefix="parity-nf2ff-")
    try:
        native_dir = os.path.join(work, "native")
        rust_dir = os.path.join(work, "rust")
        shutil.copytree(dump, native_dir)
        shutil.copytree(dump, rust_dir)
        for directory, binary in ((native_dir, os.path.expanduser("~/openems-exact/bin/nf2ff")),
                                  (rust_dir, os.path.join(REPO_ROOT, "target", "release", "nf2ff-cli"))):
            os.remove(os.path.join(directory, "nf2ff.h5"))
            subprocess.run([binary, "nf2ff.xml"], cwd=directory, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with h5py.File(os.path.join(native_dir, "nf2ff.h5")) as native, \
                h5py.File(os.path.join(rust_dir, "nf2ff.h5")) as rust:
            theta = np.asarray(native["Mesh/theta"]) * 180 / np.pi
            native_theta = np.asarray(native["nf2ff/E_theta/FD/f0_real"])[0] + 1j * np.asarray(native["nf2ff/E_theta/FD/f0_imag"])[0]
            rust_theta = np.asarray(rust["nf2ff/E_theta/FD/f0_real"])[0] + 1j * np.asarray(rust["nf2ff/E_theta/FD/f0_imag"])[0]
        fig = plt.figure(figsize=(6, 4.5))
        axis = fig.add_subplot(111, projection="polar")
        axis.plot(np.deg2rad(theta), np.abs(native_theta), lw=2, label="native")
        axis.plot(np.deg2rad(theta), np.abs(rust_theta), "--", lw=1.2, label="Rust")
        axis.set_title("nf2ff dipole E_theta pattern")
        axis.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(os.path.join(FIG_DIR, "nf2ff-parity.png"), dpi=150)
        plt.close(fig)
        peak = np.max(np.abs(native_theta)) or 1.0
        return float(np.max(np.abs(native_theta - rust_theta)) / peak)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def figure_lossy():
    work = tempfile.mkdtemp(prefix="parity-lossy-")
    try:
        x_lines = ",".join(str(value) for value in range(121))
        xml = f"""<openEMS>
  <FDTD NumberOfTimesteps="800" endCriteria="0" TimeStepMethod="3">
    <Excitation Type="0" f0="8e9" fc="8e9"/>
    <BoundaryCond xmin="PML_4" xmax="PML_4" ymin="PMC" ymax="PMC" zmin="PEC" zmax="PEC"/>
  </FDTD>
  <ContinuousStructure CoordSystem="0">
    <RectilinearGrid DeltaUnit="0.001">
      <XLines>{x_lines}</XLines>
      <YLines>0,1,2,3,4,5,6,7,8,9,10</YLines>
      <ZLines>0,1,2,3,4,5,6,7,8,9,10</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="1" Mue="1" Sigma="0" Kappa="0"/>
    <Properties>
      <Material Name="lossy">
        <Property Epsilon="1" Mue="1" Kappa="0.05" Sigma="0"/>
        <Primitives><Box Priority="1"><P1 X="-1" Y="-1" Z="-1"/><P2 X="130" Y="20" Z="20"/></Box></Primitives>
      </Material>
      <Excitation Name="src" Type="1" Excite="0,0,1">
        <Primitives><Box Priority="0"><P1 X="10" Y="0" Z="0"/><P2 X="10" Y="10" Z="10"/></Box></Primitives>
      </Excitation>
      <ProbeBox Name="p1" Type="2">
        <Primitives><Box Priority="0"><P1 X="60" Y="5" Z="5"/><P2 X="60" Y="5" Z="5"/></Box></Primitives>
      </ProbeBox>
    </Properties>
  </ContinuousStructure>
</openEMS>
"""
        for name, binary in (("native", NATIVE), ("rust", RUST)):
            directory = os.path.join(work, name)
            os.makedirs(directory)
            with open(os.path.join(directory, "lossy.xml"), "w", encoding="utf-8") as handle:
                handle.write(xml)
            subprocess.run([binary, "lossy.xml"], cwd=directory, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def trace(path):
            rows = []
            for line in open(path):
                if line.lstrip().startswith("%"):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    rows.append([float(value) for value in parts[:4]])
                except ValueError:
                    continue
            return np.array(rows)

        native = trace(os.path.join(work, "native", "p1"))
        rust = trace(os.path.join(work, "rust", "p1"))
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.plot(native[:, 0] * 1e9, native[:, 3], lw=2, label="native")
        axis.plot(rust[:, 0] * 1e9, rust[:, 3], "--", lw=1.2, label="Rust")
        axis.set_xlabel("time / ns")
        axis.set_ylabel("E_z / V/m")
        axis.set_title("Lossy guide probe at x = 60 mm (Kappa = 0.05 S/m)")
        axis.grid(True, alpha=0.3)
        axis.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(FIG_DIR, "lossy-parity.png"), dpi=150)
        plt.close(fig)
        scale = np.max(np.abs(native[:, 3])) or 1.0
        return float(np.max(np.abs(native[:, 3] - rust[:, 3])) / scale)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    os.makedirs(FIG_DIR, exist_ok=True)
    harness = load_harness()
    z_error, s21_error = figure_coax(harness)
    sheet_error = figure_conducting_sheet(harness)
    nf2ff_error = figure_nf2ff()
    lossy_error = figure_lossy()
    print(f"coax: Z {z_error:.3e}, S21 {s21_error:.3e} dB")
    print(f"conducting sheet: {sheet_error:.3f} dB")
    print(f"nf2ff: {nf2ff_error!r}")
    print(f"lossy: {lossy_error!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
