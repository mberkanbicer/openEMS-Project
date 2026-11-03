# Tutorials — openEMS (Rust migration)

Three self-contained openEMS projects that exercise the migrated solver end to
end: they open in **AppCSXCAD**, run with **openems-cli**, and produce probe and
HDF5 field dumps that `plot_tutorials.py` turns into figures with analytic
checks.

| File | Physics | Analytic reference |
|---|---|---|
| `01_free_space_pulse.xml` | Gaussian pulse in free space with PML, two probes 100 mm apart | propagation delay `Δt = 100 mm / c` |
| `02_dielectric_interface.xml` | Plane wave hitting a `εr = 4` half-space at `x = 100 mm` | Fresnel normal incidence: `Γ = -1/3`, `T = 2/3` |
| `03_rectangular_cavity.xml` | `100 × 50 × 30 mm` PEC cavity driven by a broadband source | `TE101 = 5.217 GHz`, `TE301 = 6.722 GHz` |

All three use a rectilinear `2 mm` mesh (tutorial 3 uses `2.5 mm`), `PML_8` or
`PEC` boundaries, `TimeStepMethod="3"` and `OverSampling="16"`.

## Quick start

```powershell
# from this directory
.\run_tutorial.ps1                      # GUI + run + plot, all three
.\run_tutorial.ps1 -Tutorial 03 -Mode run
.\run_tutorial.ps1 -Tutorial 02 -Mode plot -Show
```

`-Mode gui` only launches AppCSXCAD, `-Mode run` only runs the solver,
`-Mode plot` only regenerates the figures.

Without the script:

```powershell
target\release\openems-cli.exe tutorials\01_free_space_pulse.xml
python tutorials\plot_tutorials.py
```

The solver writes into the **current working directory**, so run it from (or
change into) `tutorials/results/<name>/`; `run_tutorial.ps1` does this for you.
`results/` is git-ignored.

## Requirements

- Rust workspace built with the HDF5 and GUI features:

  ```powershell
  cargo build --release -p openems-cli --features gpu
  cargo build --release -p appcsxcad
  ```

- The solver needs `hdf5.dll` and `zlib.dll` next to it (or on `PATH`). See
  `docs/migration/WINDOWS_PACKAGE.md`.
- Python with `numpy`, `h5py` and `matplotlib` for the plots. The conda
  environment `openems` on this machine has them; `run_tutorial.ps1` finds it
  automatically. Override with `-Python <path>` or `$env:OPENEMS_PYTHON`.

Tool resolution order for the script:

| Tool | 1st | 2nd | 3rd | 4th |
|---|---|---|---|---|
| solver | `-Solver` | `$env:OPENEMS_BIN` | `target\release\openems-cli.exe` | `PATH` |
| GUI | `-Gui` | `$env:APPCXCAD_BIN` | `target\release\appcsxcad.exe` | `PATH` |
| Python | `-Python` | `$env:OPENEMS_PYTHON` | conda env `openems` | `PATH` |

## What the tutorials check

`plot_tutorials.py` prints the measured numbers next to the analytic ones and
writes the figures into `results/<tutorial>/`.

### 01 — free-space pulse

- Two point probes (`Type="2"`, `Ey`) at `x = 50 mm` and `x = 150 mm`.
- Measured delay **335.1 ps** vs `100 mm / c = 333.6 ps` (**+0.46 %**); the
  residual is the `2 mm` mesh dispersion, not a solver error.
- Figures: `01_time_signals.png`, `01_spectrum.png`, `01_space_time.png`.

### 02 — dielectric half-space

- Air probe at `x = 50 mm`, dielectric probe at `x = 150 mm`, slab `εr = 4`
  from `x = 100 mm` to the PML.
- Measured **Γ = -0.324** (analytic `-1/3`) and **T = +0.671** (analytic
  `2/3`); the transmitted pulse is delayed by `50 mm / c + 50 mm / (c/2)`
  ≈ `500 ps`, measured **508 ps**.
- Figures: `02_time_signals.png`, `02_fresnel.png`, `02_space_time.png`.

### 03 — rectangular cavity

- PEC walls on all six sides, broadband excitation at the cavity centre,
  probes left/right of the source and a line dump along `x` at
  `y = 12.5 mm, z = 15 mm`.
- Measured resonances **5.209 GHz** (TE101, `-0.14 %`) and **6.715 GHz**
  (TE301, `-0.10 %`); the two probes give identical spectra, as symmetry
  requires.
- The mode profile is a single-frequency DFT of the settled field at the
  measured TE101 line: it matches `|sin(πx/a)|` with an RMS deviation of
  `0.0004`.
- `03_standing_wave.png` shows two TE101 periods of the settled field: the
  wave oscillates in place with nodes pinned to the PEC walls. The hard line
  source at `x = 50 mm` forces the field locally, so those columns are blanked
  (and excluded from the colour scaling) instead of being mistaken for a node.
- Figures: `03_spectrum.png`, `03_mode_profile.png`, `03_standing_wave.png`.

## Output files

| File | Contents |
|---|---|
| `probe_*` | text, `%` header, columns `t/s, Ex, Ey, Ez` (point probes) |
| `Et.h5`, `E_mode.h5` | native openEMS HDF5: `FieldData/TD/<8-digit step>` shaped `(3, nx, ny, nz)`, a `time` attribute per step, `Mesh/x|y|z` in metres |
| `et`, `ht` | energy-over-time logs written by the solver |
| `*.png` | figures from `plot_tutorials.py` |

`DumpBox` files are written at **every** time step (openEMS has no time
sub-sampling), so the dumps dominate runtime; the tutorials keep the dumped
region small (a line or a thin slab) and use `SubSampling` only along space.

## Editing the projects

The XML uses the openEMS project wrapper (`<openEMS>` around `<FDTD>` and
`<ContinuousStructure>`), which AppCSXCAD opens directly and which the Rust
solver accepts. `ProbeBox Type="2"` is a point E-field probe; `DumpBox
FileType="1"` selects HDF5.

The files are written without a BOM — some XML parsers reject a UTF-8 BOM, so
keep it that way if you regenerate them.

## Cross-platform note

The projects and `plot_tutorials.py` are platform independent. Only
`run_tutorial.ps1` is PowerShell; on Linux/macOS use the two direct commands
above.
