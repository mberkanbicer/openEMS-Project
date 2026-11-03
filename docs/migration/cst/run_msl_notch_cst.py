#!/usr/bin/env python3
"""Build, solve and export the openEMS MSL notch filter in CST (E-009).

Uses ``cstControlApi.py`` (the CST Python/VBA wrapper) to create the same
microstrip notch filter as
``openEMS/.github/smoketests/python/MSL_NotchFilter.py``:

    substrate  100 x 30 mm, 254 um RO4350B (eps_r 3.66)
    line       600 um wide, 35 um PEC, 100 mm long
    stub       600 um wide, 12 mm long (shunt open stub)
    ports      waveguide ports at x = +/-50 mm, 1 ... 7 GHz

It then exports a Touchstone file, reads the CST S-parameters, compares the
notch with the converged openEMS curve
(``docs/migration/reference-data/convergence/msl_notch.json``) using
``run_cst_comparison.py``, and writes a Markdown report.

Requirements
    * CST Studio Suite installed (the ``cst`` Python libraries are found by
      ``cstControlApi``; set ``CST_INSTALL_DIR`` if it is not in the default
      location).
    * A CST-compatible Python: 3.8 ... 3.13 (CST 2026 rejects 3.14).

Usage
    python docs/migration/cst/run_msl_notch_cst.py
    python docs/migration/cst/run_msl_notch_cst.py --no-run      # model only
    python docs/migration/cst/run_msl_notch_cst.py --out-dir C:/cst-run

The script closes CST at the end unless ``--keep-open`` is given.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts" / "ci"))

if not (3, 8) <= sys.version_info[:2] <= (3, 13):
    raise SystemExit(
        f"CST's Python libraries support 3.8-3.13, this interpreter is "
        f"{sys.version_info.major}.{sys.version_info.minor}. Use the Python "
        "that ships with CST or another supported interpreter."
    )

import cstControlApi as cc  # noqa: E402
from run_cst_comparison import compare, write_report  # noqa: E402

REFERENCE = REPO / "docs/migration/reference-data/convergence/msl_notch.json"


def build_model(project: "cc.CstProject", port_type: str = "waveguide",
                port_height: float = 1000.0, lines_per_wavelength: int = 160,
                adapt: bool = False, stub: bool = True,
                strip_thickness: float = 35.0, open_margin: float = 0.0) -> None:
    """Create the MSL notch geometry, ports and solver settings."""
    project.set_units("um", "GHz", "ns")
    project.set_background(epsilon=1.0, mu=1.0)

    # Ports sit on the x planes; zmin is the ground plane. The lateral and top
    # boundaries can be pushed into open space (expanded open) so the absorber
    # is not glued to the substrate edge.
    if open_margin > 0:
        project.set_boundaries(
            xmin="open", xmax="open",
            ymin="expanded open", ymax="expanded open",
            zmin="electric", zmax="expanded open",
            open_add_space_factor=open_margin,
        )
    else:
        project.set_boundaries(
            xmin="open", xmax="open",
            ymin="open", ymax="open",
            zmin="electric", zmax="open",
        )

    project.add_material("RO4350B", epsilon=3.66, mu=1.0, tan_delta=0.0)

    # Substrate: 100 mm x 30 mm x 254 um, stub area included.
    project.define_brick(
        "substrate",
        (-50000, 50000), (-9000, 21000), (0, 254),
        material="RO4350B", component="dielectric",
    )
    # 35 um PEC strip and stub (openEMS uses a zero-thickness PEC sheet).
    project.define_brick(
        "strip",
        (-50000, 50000), (-300, 300), (254, 254 + strip_thickness),
        material="PEC", component="metal",
    )
    if stub:
        project.define_brick(
            "stub",
            (-300, 300), (300, 12300), (254, 254 + strip_thickness),
            material="PEC", component="metal",
        )
    # Air above the strip up to the openEMS domain top (3 mm). Without this the
    # open zmax boundary would sit just above the strip and detune the line.
    project.define_brick(
        "air",
        (-50000, 50000), (-9000, 21000), (254 + strip_thickness, 3000),
        material="Vacuum", component="air",
    )

    # Waveguide ports over the substrate cross-section at both line ends. The
    # port plane must contain the strip (z = 254..289), otherwise CST resolves
    # a parallel-plate mode with a ~4 GHz cutoff instead of the microstrip mode.
    # A discrete 50 ohm edge port is offered for cases where the waveguide
    # mode is not matched (CST then shows port-to-stub ripple).
    for number, x in ((1, -50000), (2, 50000)):
        if port_type == "waveguide":
            project.add_waveguide_port(
                number,
                orientation="xmin" if x < 0 else "xmax",
                coordinates="Free",
                x_range=(x, x),
                y_range=(-3000, 3000),
                z_range=(0, port_height),
                modes=1,
                port_on_bound=True,
                label=f"port{number}",
            )
        elif port_type == "discrete":
            # Keep at least three mesh steps from the open boundary: inset the
            # lumped port by 2 mm; the 2 mm overhang is electrically negligible
            # below 7 GHz.
            inset = 2000.0
            project.add_discrete_port(
                number,
                (x - inset if x > 0 else x + inset, 0, 254),
                (x - inset if x > 0 else x + inset, 0, 0),
                kind="Sparameter",
                impedance=50.0,
                monitor=True,
            )
        else:
            raise ValueError(f"unknown port type: {port_type!r}")

    project.set_solver("HF Time Domain")
    project.set_frequency_range(1.0, 7.0)
    project.set_frequency_samples(1201)
    project.set_time_domain(
        mesh_adaption=adapt,
        auto_norm_impedance=False,
        norming_impedance=50.0,
    )
    # Global mesh: CST's documented MeshSettings.Set keys. The plain
    # Mesh.LinesPerWavelength property is silently ignored on this release, so
    # the density must go through MeshSettings.
    project.configure_vba_object(
        "Mesh", caption="mesh type", reset=False,
        settings={"MeshType": "PBA"},
        extra=['.SetCreator "High Frequency"'],
    )
    project.configure_vba_object(
        "MeshSettings", caption="mesh density", reset=False,
        extra=[
            '.SetMeshType "Hex"',
            f'.Set "StepsPerWaveNear", {lines_per_wavelength}',
            f'.Set "StepsPerWaveFar", {lines_per_wavelength}',
            '.Set "RatioLimit", 2',
        ],
    )


def read_port(project_path: Path, item: str) -> tuple[list[float], list[complex]]:
    """Read one S-parameter from the saved project, returning Hz and complex values."""
    cst = cc.load_cst()
    results = cst.results.ProjectFile(str(project_path), allow_interactive=True).get_3d()
    result = results.get_result_item(item)
    xs = list(result.get_xdata())
    ys = [complex(value) for value in result.get_ydata()]
    unit = str(getattr(result, "xunit", "") or "").lower()
    scale = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}.get(unit)
    if scale is None:
        # No unit attribute: infer from the magnitude of the axis.
        peak = max((abs(value) for value in xs), default=0.0)
        scale = 1.0 if peak > 1e7 else 1e9 if peak < 1e3 else 1e6
    return [value * scale for value in xs], ys


def write_touchstone(path: Path, freqs: list[float],
                     s11: list[complex], s21: list[complex]) -> None:
    """Write a 2-port Touchstone file in Hz/RI (S12 = S21, reciprocal)."""
    lines = [
        "! CST export from run_msl_notch_cst.py (openEMS MSL notch reference)",
        "! substrate RO4350B 3.66, 254 um; line 600 um; stub 12 mm; ports at x=+/-50 mm",
        "# Hz S RI R 50",
    ]
    for f, a, b in zip(freqs, s11, s21):
        lines.append(
            f"{f:.6e} "
            f"{a.real:.10e} {a.imag:.10e} "
            f"{b.real:.10e} {b.imag:.10e} "
            f"{b.real:.10e} {b.imag:.10e} "
            f"{a.real:.10e} {a.imag:.10e}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=HERE / "run")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--no-run", action="store_true", help="build and save only")
    parser.add_argument("--keep-open", action="store_true", help="leave CST running")
    parser.add_argument("--port-type", choices=("waveguide", "discrete"),
                        default="waveguide")
    parser.add_argument("--port-height", type=float, default=1000.0,
                        help="waveguide port plane height in um (z = 0 .. height)")
    parser.add_argument("--lines-per-wavelength", type=int, default=160)
    parser.add_argument("--adapt", action="store_true",
                        help="enable adaptive mesh refinement (the validated run uses a fixed 160 steps/lambda mesh)")
    parser.add_argument("--no-stub", action="store_true",
                        help="omit the shunt stub (port/line diagnostic)")
    parser.add_argument("--no-compare", action="store_true",
                        help="stop after the Touchstone export (diagnostics)")
    parser.add_argument("--strip-thickness", type=float, default=35.0,
                        help="PEC strip/stub thickness in um (openEMS uses 0)")
    parser.add_argument("--open-margin", type=float, default=0.0,
                        help="expanded-open space factor for y/zmax (0 = boundary at the substrate edge)")
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    project_path = (args.project or (out_dir / "msl_notch.cst")).resolve()

    session = cc.CstSession().start()
    project = None
    try:
        project = session.new_mws()
        build_model(project,
                    port_type=args.port_type,
                    port_height=args.port_height,
                    lines_per_wavelength=args.lines_per_wavelength,
                    adapt=args.adapt,
                    stub=not args.no_stub,
                    strip_thickness=args.strip_thickness,
                    open_margin=args.open_margin)
        project.save(project_path)
        print(f"model saved: {project_path}")

        if args.no_run:
            print("--no-run: solver not started")
            return 0

        started = time.time()
        print("running CST time-domain solver ... (this can take several minutes)")
        project.run_solver()
        print(f"solver finished in {time.time() - started:.1f}s")
        project.save(project_path)

        freqs, s11 = read_port(project_path, "1D Results\\S-Parameters\\S1,1")
        _, s21 = read_port(project_path, "1D Results\\S-Parameters\\S2,1")
        if not freqs:
            raise RuntimeError("CST returned no S-parameter samples")

        try:
            messages = project.messages()
            (out_dir / "cst_messages.txt").write_text(
                str(messages), encoding="utf-8", errors="replace")
        except Exception:
            pass

        touchstone = out_dir / "msl_notch.s2p"
        write_touchstone(touchstone, freqs, s11, s21)
        print(f"touchstone: {touchstone} ({len(freqs)} samples)")

        if args.no_compare:
            return 0

        rows = [(f, a, b) for f, a, b in zip(freqs, s11, s21)]
        result = compare(REFERENCE, rows)
        report = out_dir / "msl_notch_comparison.md"
        write_report(result, report)

        metadata = {
            "project": str(project_path),
            "touchstone": str(touchstone),
            "samples": len(freqs),
            "frequency_hz": [min(freqs), max(freqs)],
            "cst_notch_hz": result["cst_notch_hz"],
            "cst_s11_at_notch": result["cst_s11_at_notch"],
            "cst_s21_at_notch_db": result["cst_s21_at_notch_db"],
            "reference_notch_hz": result["reference_notch_hz"],
            "notch_relative_difference": result["notch_relative_difference"],
            "gates": result["gates"],
            "passed": result["passed"],
        }
        (out_dir / "msl_notch_cst.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8")

        print()
        print(f"CST notch        : {result['cst_notch_hz'] / 1e9:.4f} GHz "
              f"(|S11| {result['cst_s11_at_notch']:.4f}, "
              f"|S21| {result['cst_s21_at_notch_db']:.1f} dB)")
        print(f"openEMS notch    : {result['reference_notch_hz'] / 1e9:.4f} GHz")
        print(f"relative diff    : {result['notch_relative_difference'] * 100:.3f} %")
        for name, passed in result["gates"].items():
            print(f"  {name:22s} {'PASS' if passed else 'FAIL'}")
        print(f"report           : {report}")
        print("CST comparison   :", "PASS" if result["passed"] else "FAIL")
        return 0 if result["passed"] else 1
    except Exception:
        if project is not None:
            try:
                print("CST messages:")
                print(project.messages())
            except Exception:
                pass
        raise
    finally:
        if project is not None and not args.keep_open:
            try:
                project.close(save=False)
            except Exception:
                pass
        if not args.keep_open:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
