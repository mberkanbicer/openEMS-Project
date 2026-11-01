#!/usr/bin/env python3
"""Plot the results of the three openEMS Rust tutorials.

The tutorials are plain openEMS/CSXCAD XML projects in this directory.  Run
them with ``openems-cli`` (or ``run_tutorial.ps1``) so that the probe files and
the HDF5 field dumps land in ``results/<tutorial>/``; then run this script.

    python plot_tutorials.py                 # all tutorials
    python plot_tutorials.py --only 02       # one tutorial
    python plot_tutorials.py --show          # also open a window

Requires numpy, h5py and matplotlib.  On this machine the openEMS conda
environment provides them:

    C:\\Users\\...\\miniconda3\\envs\\openems\\python.exe plot_tutorials.py

Every figure is written next to the data as a PNG; the numeric checks
(delay, Fresnel coefficients, cavity resonances) are printed to stdout.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

C0 = 299_792_458.0  # speed of light in vacuum, m/s

# Analytic references used by the tutorials.
T1_DISTANCE = 0.100  # probe separation in m
T2_EPS_R = 4.0
T2_GAMMA = (1.0 - np.sqrt(T2_EPS_R)) / (1.0 + np.sqrt(T2_EPS_R))  # -1/3
T2_TAU = 2.0 / (1.0 + np.sqrt(T2_EPS_R))  # 2/3
T3_A, T3_B, T3_D = 0.100, 0.050, 0.030  # cavity dimensions in m
T3_MODES = [
    ("TE101", 1, 0, 1),
    ("TE301", 3, 0, 1),
    ("TE111", 1, 1, 1),
    ("TE201", 2, 0, 1),
]


# --------------------------------------------------------------------------- io
def load_probe(results: str, name: str) -> np.ndarray:
    """Load a probe file: columns ``t/s, Ex, Ey, Ez`` (Type 2 probes)."""
    path = os.path.join(results, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"missing probe file '{path}'\n"
            "run the tutorial first (see README.md / run_tutorial.ps1)"
        )
    data = np.loadtxt(path, comments="%")
    return np.atleast_2d(data)


def load_dump(results: str, name: str):
    """Load a time-domain HDF5 dump.

    Returns ``(times, coords, field)`` with ``field`` shaped
    ``(n_frames, n_x)`` for a line dump along x and ``coords`` in metres.
    """
    import h5py

    path = os.path.join(results, f"{name}.h5")
    if not os.path.exists(path):
        raise FileNotFoundError(f"missing dump file '{path}'")

    with h5py.File(path, "r") as handle:
        group = handle["FieldData/TD"]
        keys = sorted(group.keys())
        first = group[keys[0]]
        # (component, nx, ny, nz); the tutorials dump a line along x.
        shape = first.shape
        nx, ny, nz = shape[1], shape[2], shape[3]
        axis = int(np.argmax(shape[1:])) + 1
        mesh_name = {1: "x", 2: "y", 3: "z"}[axis]
        coords = handle[f"Mesh/{mesh_name}"][:]
        times = np.array(
            [float(np.ravel(group[key].attrs["time"])[0]) for key in keys]
        )
        # Component 1 is Ey for the tutorials; fall back to the largest one.
        component = 1 if shape[0] > 1 else 0
        values = np.array([group[key][component] for key in keys], dtype=np.float64)
    values = values.reshape(len(keys), -1)
    return times, coords, values


def spectrum(signal: np.ndarray, dt: float):
    window = np.hanning(len(signal))
    values = np.fft.rfft(signal * window)
    freqs = np.fft.rfftfreq(len(signal), dt)
    return freqs, np.abs(values)


def save(fig, path: str, show: bool):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"  wrote {path}")
    if show:
        plt.show()
    plt.close(fig)


def header(title: str):
    print(f"\n=== {title} ===")


# ------------------------------------------------------------------ tutorial 1
def plot_01(results: str, show: bool):
    header("01 free-space Gaussian pulse")
    near = load_probe(results, "probe_near")
    far = load_probe(results, "probe_far")
    dt = float(near[1, 0] - near[0, 0])

    i_near = int(np.argmax(np.abs(near[:, 2])))
    i_far = int(np.argmax(np.abs(far[:, 2])))
    delay = far[i_far, 0] - near[i_near, 0]
    expected = T1_DISTANCE / C0
    print(f"  probe peak: near {near[i_near, 2]:.4f} V/m @ {near[i_near, 0]*1e9:.3f} ns")
    print(f"              far  {far[i_far, 2]:.4f} V/m @ {far[i_far, 0]*1e9:.3f} ns")
    print(
        f"  propagation delay {delay*1e12:.2f} ps, expected {expected*1e12:.2f} ps "
        f"({100*(delay-expected)/expected:+.2f} %)"
    )

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(near[:, 0] * 1e9, near[:, 2], label="probe at x = 50 mm")
    ax.plot(far[:, 0] * 1e9, far[:, 2], label="probe at x = 150 mm")
    ax.axvline(near[i_near, 0] * 1e9, color="0.4", ls=":")
    ax.axvline(far[i_far, 0] * 1e9, color="0.4", ls=":")
    ax.annotate(
        "",
        xy=(far[i_far, 0] * 1e9, 0.55),
        xytext=(near[i_near, 0] * 1e9, 0.55),
        arrowprops=dict(arrowstyle="<->", color="tab:red"),
    )
    ax.text(
        0.5 * (near[i_near, 0] + far[i_far, 0]) * 1e9,
        0.62,
        f"$\\Delta t$ = {delay*1e12:.1f} ps  (100 mm / c = {expected*1e12:.1f} ps)",
        color="tab:red",
        ha="center",
    )
    ax.set_xlabel("time / ns")
    ax.set_ylabel("$E_y$ / (V/m)")
    ax.set_title("Free-space Gaussian pulse: propagation delay")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    save(fig, os.path.join(results, "01_time_signals.png"), show)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for data, label in ((near, "x = 50 mm"), (far, "x = 150 mm")):
        f, a = spectrum(data[:, 2], dt)
        ax.plot(f / 1e9, a / a.max(), label=label)
    ax.set_xlim(0, 10)
    ax.set_xlabel("frequency / GHz")
    ax.set_ylabel("normalized |FFT|")
    ax.set_title("Free-space pulse spectrum (identical at both probes)")
    ax.grid(alpha=0.3)
    ax.legend()
    save(fig, os.path.join(results, "01_spectrum.png"), show)

    try:
        times, xs, field = load_dump(results, "Et")
        step = max(1, len(times) // 400)
        fig, ax = plt.subplots(figsize=(9, 4.6))
        mesh = ax.pcolormesh(
            xs * 1e3,
            times[::step] * 1e9,
            field[::step],
            shading="auto",
            cmap="RdBu_r",
            vmin=-0.6 * np.abs(field).max(),
            vmax=0.6 * np.abs(field).max(),
        )
        ax.set_xlabel("x / mm")
        ax.set_ylabel("time / ns")
        ax.set_title("$E_y(x,t)$: the pulse travels at the speed of light")
        fig.colorbar(mesh, ax=ax, label="$E_y$ / (V/m)")
        save(fig, os.path.join(results, "01_space_time.png"), show)
    except FileNotFoundError as error:
        print(f"  (skipped space-time plot: {error})")


# ------------------------------------------------------------------ tutorial 2
def plot_02(results: str, show: bool):
    header("02 dielectric half-space (Fresnel)")
    air = load_probe(results, "probe_air")
    diel = load_probe(results, "probe_dielectric")
    dt = float(air[1, 0] - air[0, 0])

    i_inc = int(np.argmax(np.abs(air[:, 2])))
    t_inc = air[i_inc, 0]
    incident = air[i_inc, 2]

    # The reflected pulse returns after 2 x 50 mm of air (~333 ps), clearly
    # separated from the incident one.
    window = (air[:, 0] > t_inc + 0.15e-9) & (air[:, 0] < t_inc + 0.55e-9)
    if not window.any():
        window = air[:, 0] > t_inc
    i_ref = np.argmin(np.where(window, air[:, 2], np.inf))
    reflected = air[i_ref, 2]

    i_tr = int(np.argmax(np.abs(diel[:, 2])))
    transmitted = diel[i_tr, 2]

    gamma = reflected / incident
    tau = transmitted / incident
    print(f"  incident    {incident:+.4f} V/m @ {t_inc*1e9:.3f} ns")
    print(f"  reflected   {reflected:+.4f} V/m @ {air[i_ref, 0]*1e9:.3f} ns")
    print(f"  transmitted {transmitted:+.4f} V/m @ {diel[i_tr, 0]*1e9:.3f} ns")
    print(f"  Gamma = {gamma:+.4f}  (analytic {T2_GAMMA:+.4f})")
    print(f"  T     = {tau:+.4f}  (analytic {T2_TAU:+.4f})")
    print(f"  1 + Gamma = {1+gamma:+.4f} vs T = {tau:+.4f}")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(air[:, 0] * 1e9, air[:, 2], label="air probe, x = 50 mm")
    ax.plot(diel[:, 0] * 1e9, diel[:, 2], label="dielectric probe, x = 150 mm")
    for index, data, text, offset in (
        (i_inc, air, "incident", 14),
        (i_ref, air, "reflected", -14),
        (i_tr, diel, "transmitted", 14),
    ):
        ax.annotate(
            text,
            xy=(data[index, 0] * 1e9, data[index, 2]),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if offset > 0 else "top",
            fontsize=8,
            arrowprops=dict(arrowstyle="-", color="0.4", lw=0.7),
        )
    ax.axhline(0, color="0.7", lw=0.6)
    ax.set_ylim(bottom=-0.45, top=1.02)
    ax.set_xlabel("time / ns")
    ax.set_ylabel("$E_y$ / (V/m)")
    ax.set_title("Dielectric interface: incident, reflected and transmitted pulses")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")
    save(fig, os.path.join(results, "02_time_signals.png"), show)

    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["$\\Gamma$ (reflection)", "$T$ (transmission)"]
    measured = [gamma, tau]
    analytic = [T2_GAMMA, T2_TAU]
    x = np.arange(2)
    ax.bar(x - 0.18, measured, 0.36, label="FDTD")
    ax.bar(x + 0.18, analytic, 0.36, label="Fresnel")
    for index, value in enumerate(measured):
        ax.text(index - 0.18, value + 0.02, f"{value:+.3f}", ha="center", fontsize=8)
    for index, value in enumerate(analytic):
        ax.text(index + 0.18, value + 0.02, f"{value:+.3f}", ha="center", fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylim(-0.5, 0.85)
    ax.axhline(0, color="0.7", lw=0.6)
    ax.set_ylabel("coefficient")
    ax.set_title(f"Fresnel coefficients, $\\varepsilon_r$ = {T2_EPS_R:g}")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    save(fig, os.path.join(results, "02_fresnel.png"), show)

    try:
        times, xs, field = load_dump(results, "Et")
        step = max(1, len(times) // 400)
        fig, ax = plt.subplots(figsize=(9, 4.6))
        mesh = ax.pcolormesh(
            xs * 1e3,
            times[::step] * 1e9,
            field[::step],
            shading="auto",
            cmap="RdBu_r",
            vmin=-0.6 * np.abs(field).max(),
            vmax=0.6 * np.abs(field).max(),
        )
        ax.axvline(100, color="k", lw=0.8, ls="--")
        ax.text(101, times[-1] * 0.05e9, "$\\varepsilon_r$ = 4", fontsize=8)
        ax.set_xlabel("x / mm")
        ax.set_ylabel("time / ns")
        ax.set_title("$E_y(x,t)$: the transmitted pulse slows down in the dielectric")
        fig.colorbar(mesh, ax=ax, label="$E_y$ / (V/m)")
        save(fig, os.path.join(results, "02_space_time.png"), show)
    except FileNotFoundError as error:
        print(f"  (skipped space-time plot: {error})")


# ------------------------------------------------------------------ tutorial 3
def analytic_modes():
    modes = []
    for name, m, n, p in T3_MODES:
        frequency = (
            C0
            / 2.0
            * np.sqrt((m / T3_A) ** 2 + (n / T3_B) ** 2 + (p / T3_D) ** 2)
        )
        modes.append((name, frequency))
    return modes


def plot_03(results: str, show: bool):
    header("03 PEC rectangular cavity")
    left = load_probe(results, "probe_left")
    right = load_probe(results, "probe_right")
    dt = float(left[1, 0] - left[0, 0])
    duration = left[-1, 0]
    print(f"  {len(left)} samples, dt = {dt*1e12:.4f} ps, T = {duration*1e9:.2f} ns")
    print(f"  frequency resolution = {1/duration/1e6:.1f} MHz")

    freqs, amp = spectrum(left[:, 2], dt)
    freqs_r, amp_r = spectrum(right[:, 2], dt)
    band = (freqs >= 2.5e9) & (freqs <= 8.0e9)
    band_r = (freqs_r >= 2.5e9) & (freqs_r <= 8.0e9)

    modes = analytic_modes()
    print("  analytic TE modes:")
    for name, frequency in modes:
        print(f"    {name:6s} {frequency/1e9:.3f} GHz")

    # Locate the measured peaks (local maxima above 5 % of the maximum) and
    # drop the Hanning-window sidelobes of a line that was already accepted.
    local = np.where(
        (amp[band][1:-1] > amp[band][:-2])
        & (amp[band][1:-1] > amp[band][2:])
        & (amp[band][1:-1] > 0.05 * amp[band].max())
    )[0] + 1
    peak_freqs = freqs[band][local]
    peak_amps = amp[band][local]
    accepted: list[float] = []
    for index in np.argsort(peak_amps)[::-1]:
        frequency = float(peak_freqs[index])
        if all(abs(frequency - other) > 5.0 / duration for other in accepted):
            accepted.append(frequency)
        if len(accepted) == 4:
            break
    print("  measured peaks:")
    for frequency in accepted:
        nearest = min(modes, key=lambda item: abs(item[1] - frequency))
        error = 100 * (frequency - nearest[1]) / nearest[1]
        print(
            f"    {frequency/1e9:.3f} GHz  -> {nearest[0]} "
            f"({nearest[1]/1e9:.3f} GHz, {error:+.2f} %)"
        )
    # The dominant line is the TE101 resonance; its exact measured frequency
    # is used for the mode-profile DFT below.
    te101 = min(accepted, key=lambda value: abs(value - modes[0][1]))
    print(f"  dominant line {te101/1e9:.4f} GHz used for the mode profile")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(freqs[band] / 1e9, amp[band] / amp[band].max(), label="probe left")
    ax.plot(freqs_r[band_r] / 1e9, amp_r[band_r] / amp_r[band_r].max(), "--", label="probe right")
    for name, frequency in modes:
        ax.axvline(frequency / 1e9, color="tab:red", lw=0.8, ls=":")
        ax.text(frequency / 1e9, 0.95, name, rotation=90, fontsize=7, color="tab:red", va="top")
    ax.set_xlim(2.5, 8.0)
    ax.set_xlabel("frequency / GHz")
    ax.set_ylabel("normalized |FFT|")
    ax.set_title("Cavity spectrum and analytic TE modes")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")
    save(fig, os.path.join(results, "03_spectrum.png"), show)

    try:
        times, xs, field = load_dump(results, "E_mode")
        # Complex DFT of the settled field at the measured TE101 line. The
        # time-domain RMS mixes every excited mode and is dominated by the
        # broadband source transient; the single-frequency DFT isolates the
        # standing-wave mode shape.
        settled = times > 5e-9
        ts = times[settled]
        data = field[settled]
        amplitude = np.abs(data.T @ np.exp(-2j * np.pi * te101 * ts)) / len(ts) * 2.0
        amplitude = amplitude / amplitude.max()
        reference = np.abs(np.sin(np.pi * xs / T3_A))
        reference = reference / reference.max()
        deviation = float(np.sqrt(np.mean((amplitude - reference) ** 2)))
        print(
            f"  TE101 mode profile: RMS deviation from |sin(pi x/a)| = {deviation:.4f}"
        )
        fig, ax = plt.subplots(figsize=(9, 4.2))
        ax.plot(
            xs * 1e3,
            amplitude,
            "o-",
            ms=3,
            lw=1.2,
            label=f"FDTD DFT @ {te101/1e9:.3f} GHz",
        )
        ax.plot(
            xs * 1e3,
            reference,
            "k--",
            lw=1.0,
            label="$|\\sin(\\pi x/a)|$ (TE101)",
        )
        ax.set_xlabel("x / mm")
        ax.set_ylabel("normalized $E_y$ amplitude")
        ax.set_title("TE101 standing-wave mode profile along the cavity")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        save(fig, os.path.join(results, "03_mode_profile.png"), show)

        step = max(1, len(times) // 400)
        # Two TE101 periods of the settled field: the standing wave oscillates
        # in place, with nodes pinned to the PEC walls.  The hard line source
        # at x = 50 mm is excluded from the colour scaling so its near field
        # does not swamp the mode.
        period = 1.0 / te101
        t0 = 20e-9
        window = (times >= t0) & (times <= t0 + 2.0 * period)
        if not window.any():
            window = np.ones_like(times, dtype=bool)
        frames = np.where(window)[0]
        xs_mm = xs * 1e3
        source = np.abs(xs_mm - 50.0) <= 2.5
        scale = float(
            np.percentile(np.abs(field[frames][:, ~source]), 99.5)
            if (~source).any()
            else np.abs(field[frames]).max()
        )
        # Blank the source columns: the hard line source forces the field
        # there and would otherwise read as a spurious node in the mode.
        visible = field[frames].copy()
        visible[:, source] = np.nan
        fig, ax = plt.subplots(figsize=(9, 4.6))
        mesh = ax.pcolormesh(
            xs_mm,
            times[frames] * 1e9,
            visible,
            shading="auto",
            cmap="RdBu_r",
            vmin=-scale,
            vmax=scale,
        )
        ax.axvline(50, color="k", lw=0.8, ls="--")
        ax.text(
            50.8,
            times[frames][-1] * 1e9,
            "line source (masked)",
            fontsize=8,
            va="top",
            bbox=dict(facecolor="white", alpha=0.75, edgecolor="none", pad=1.5),
        )
        ax.set_xlabel("x / mm")
        ax.set_ylabel("time / ns")
        ax.set_title(
            f"$E_y(x,t)$ over two TE101 periods: nodes pinned to the PEC walls"
        )
        fig.colorbar(mesh, ax=ax, label="$E_y$ / (V/m)")
        save(fig, os.path.join(results, "03_standing_wave.png"), show)
    except FileNotFoundError as error:
        print(f"  (skipped field plots: {error})")


# ------------------------------------------------------------------------ main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"),
        help="directory holding the tutorial result folders (default: ./results)",
    )
    parser.add_argument(
        "--only",
        choices=["01", "02", "03"],
        action="append",
        help="plot only the given tutorial (repeatable)",
    )
    parser.add_argument("--show", action="store_true", help="also open the figures")
    args = parser.parse_args(argv)

    tutorials = {
        "01": ("01_free_space_pulse", plot_01),
        "02": ("02_dielectric_interface", plot_02),
        "03": ("03_rectangular_cavity", plot_03),
    }
    selected = args.only or list(tutorials)
    failures = 0
    for key in selected:
        folder, function = tutorials[key]
        results = os.path.join(args.results, folder)
        try:
            function(results, args.show)
        except FileNotFoundError as error:
            failures += 1
            print(f"\n=== tutorial {key}: {error}", file=sys.stderr)
    if failures:
        print(f"\n{failures} tutorial(s) had no results to plot.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
