# Tutorials — end-to-end user workflow (GUI, solver, plots)

**Status (2026-11-02): Verified on Windows (local acceptance host).**

Three self-contained openEMS project files live in `tutorials/` at the root of
the repository (outside the submodules, so no submodule pointer churn). Each
one can be opened in the Rust `appcsxcad`, simulated with the Rust
`openems-cli`, and plotted with the bundled Python script. They exist to give
the migrated stack a user-facing workflow, distinct from the scientific
differential suites, and every analytic number below was re-measured with the
final binaries on 2026-11-02.

| Tutorial | Physics | Analytic reference |
|---|---|---|
| `tutorials/01_free_space_pulse.xml` | Gaussian plane pulse in free space, `PML_8` in x, two point probes 100 mm apart | propagation delay `100 mm / c` |
| `tutorials/02_dielectric_interface.xml` | Plane pulse onto a `eps_r = 4` half-space starting at `x = 100 mm` | Fresnel normal incidence `Gamma = -1/3`, `T = 2/3` |
| `tutorials/03_rectangular_cavity.xml` | `100 x 50 x 30 mm` PEC cavity, broadband line source | `TE101 = 5.217 GHz`, `TE301 = 6.722 GHz`, `sin(pi x/a)` profile |

All three use explicit rectilinear meshes (2 mm; the cavity 2.5 mm),
`TimeStepMethod="3"`, `OverSampling="16"`, point probes with `Type="2"` and
HDF5 dump boxes with `FileType="1"`. The files are written without a BOM.

## Workflow

```powershell
# from tutorials/ (Windows helper; the XML and the plot script are platform
# independent, only the .ps1 is PowerShell)
.\run_tutorial.ps1                      # GUI + run + plot, all three
.\run_tutorial.ps1 -Tutorial 03 -Mode run
.\run_tutorial.ps1 -Tutorial 02 -Mode plot -Show
```

`run_tutorial.ps1` resolves the solver (`-Solver` / `$env:OPENEMS_BIN` /
`target\release\openems-cli.exe` / PATH), the GUI (`-Gui` /
`$env:APPCXCAD_BIN` / `target\release\appcsxcad.exe` / PATH) and a Python that
actually imports numpy/h5py/matplotlib (`-Python` / `$env:OPENEMS_PYTHON` /
conda env `openems` / `$env:CONDA_PREFIX` / PATH), runs the solver with the
results directory as working directory, and invokes `plot_tutorials.py`.

## Verification evidence (2026-11-02, final binaries)

### GUI

Each project was opened with `Start-Process appcsxcad.exe <xml> -PassThru`;
after 6 s every process was alive and its window title carried the loaded
project path, then it was closed:

```
01_free_space_pulse.xml      alive=yes title='AppCSXCAD - ...\tutorials\01_free_space_pulse.xml'
02_dielectric_interface.xml  alive=yes title='AppCSXCAD - ...\tutorials\02_dielectric_interface.xml'
03_rectangular_cavity.xml    alive=yes title='AppCSXCAD - ...\tutorials\03_rectangular_cavity.xml'
```

`AppCSXCAD::load_path` accepts the `<openEMS>` wrapper format (FDTD +
ContinuousStructure), which is what makes the same file usable by the GUI and
the solver.

### Solver runs

`run_tutorial.ps1 -Mode run` (700/800/12000 timesteps):

```
==> run 01_free_space_pulse     completed: 700 timesteps   0.41 s   exit 0
==> run 02_dielectric_interface completed: 800 timesteps   0.40 s   exit 0
==> run 03_rectangular_cavity   completed: 12000 timesteps 2.70 s   exit 0
```

The "Max. number of timesteps reached before end-criteria" warning is expected:
the step counts are fixed so the runs stay short.

### Physics checks (`plot_tutorials.py` output)

Tutorial 1:

```
probe peak: near 0.8711 V/m @ 0.354 ns
            far  0.8713 V/m @ 0.689 ns
propagation delay 335.09 ps, expected 333.56 ps (+0.46 %)
```

Tutorial 2:

```
incident    +0.8711 V/m @ 0.354 ns
reflected   -0.2821 V/m @ 0.689 ns
transmitted +0.5842 V/m @ 0.863 ns
Gamma = -0.3239  (analytic -0.3333)
T     = +0.6707  (analytic +0.6667)
1 + Gamma = +0.6761 vs T = +0.6707
```

Tutorial 3 (57.77 ns record, 17.3 MHz resolution):

```
measured peaks:
  5.209 GHz  -> TE101 (5.217 GHz, -0.14 %)
  6.715 GHz  -> TE301 (6.722 GHz, -0.10 %)
TE101 mode profile: RMS deviation from |sin(pi x/a)| = 0.0004
```

The left and right cavity probes give identical spectra (symmetry). The mode
profile is a single-frequency complex DFT of the settled dump at the measured
TE101 line — not an RMS over time, which mixes the broadband source transient
into the profile. Nine PNG figures are written under `tutorials/results/`
(three per tutorial; `results/` is git-ignored).

The residual +0.46 % delay error of tutorial 1 is the 2 mm mesh dispersion of
the second-order FDTD scheme, and the same mechanism explains the small
Fresnel and resonance offsets. No tolerance was widened to obtain these
numbers.

## Solver changes made while building the tutorials

Three changes were needed to make the workflow usable; all are numerically
neutral and were verified separately.

1. **Probe time-domain writer keeps its stream open**
   (`openEMS/rust/src/processing_integral.rs`). The port re-opened and
   re-closed the probe file once per timestep, costing ~9 ms per step on
   Windows and dominating any probe run (tutorial 1: 61 s -> 0.34 s after both
   writer fixes). The native `ProcessIntegral` holds an `ofstream` member for
   the whole run; the Rust port now keeps a `File` in the struct and closes it
   in `post_process`/`reset`. Unit tests: 7/7 `processing_integral` tests pass.

2. **HDF5 dump writer keeps its file open**
   (`openEMS/rust/src/processing.rs`, `HDF5FileWriter`). Same defect for
   `DumpBox` output: opening/closing the HDF5 file per timestep also bloated
   the file (repeated object headers): `Et.h5` for tutorial 1 shrank from
   9.68 MB to 0.79 MB with identical content (1501 frames of `(3, 11, 1, 1)`
   plus `time` attributes). `ProcessFieldsTD` now caches the writer and closes
   it in `post_process`/`reset`; `ProcessFieldsFD::dump_hdf5` uses the same
   handle API.

   Numerical neutrality: with dumps enabled vs `--disable-dumps`, the tutorial
   1 probe files `probe_near`, `probe_far`, `et` and `ht` are **byte-identical
   (SHA-256)**, and the probe files after the change are unchanged from before
   it.

3. **`--disable-dumps` actually disables the field dumps**
   (`openEMS/rust/src/openems.rs`, `processing.rs`). The flag only suppressed
   the `et`/`ht` excitation files while every `DumpBox` still ran and wrote —
   the opposite of native, which creates the dump processings but calls
   `ProcField->SetEnable(Enable_Dumps)` (`openems.cpp:717`) and still writes
   `et`/`ht` unconditionally (`openems.cpp:1421`). `ProcessFieldsTD`,
   `ProcessFieldsFD` and `ProcessFieldsSAR` now carry the `enabled` flag
   (`process_fields` returns `-1`, `post_process` writes nothing), all four
   dump branches in `setup_csx_dumps` apply `set_enable(self.enable_dumps)`,
   and `et`/`ht` are written unconditionally as in native.

   Verification: `01_free_space_pulse.xml --disable-dumps` writes only
   `et`, `ht`, `probe_near`, `probe_far` (no `Et.h5`), exit 0; an FD-dump
   variant (`DumpType="10"` with `Frequency="5e9"`) writes
   `FieldData/FD/f0 (3, 51, 1, 1) @ 5 GHz` with dumps enabled and no HDF5 file
   with `--disable-dumps`; the full `openems-core` suite passes (308 + 2
   analytic tests).

## Environment

- Windows 11, Rust workspace built with `--features hdf5,gpu` against the
  conda `openems` environment's HDF5 1.10.6 (`hdf5.dll` + `zlib.dll` next to
  the executables; see `WINDOWS_PACKAGE.md`).
- Python: the conda `openems` environment (numpy 1.26.4, h5py 3.7.0,
  matplotlib 3.9.1).
- Binaries: `target/release/openems-cli.exe`, `target/release/appcsxcad.exe`
  at `openEMS@a7d33e4` plus the three changes above.

## Known limits

- `DumpBox` files are written every timestep (openEMS has no time
  sub-sampling); the tutorials therefore dump a line and use spatial
  `SubSampling` only. Larger dumped regions dominate the runtime by design.
- `run_tutorial.ps1` is Windows/PowerShell; the projects and
  `plot_tutorials.py` are platform independent.
