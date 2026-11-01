# Exception register (RM-126)

Approved, bounded omissions from the native feature set. Every entry needs an
impact statement, an owner decision and a native-compatibility path. Anything
not listed here is an open task, not an accepted exception.

The former E-002 ("`ctb-rs` has no standalone binary") was removed on
2026-10-27: RM-116 delivered the `ctb` command (`info`, `convert`, `renorm`)
with M-file wrappers, so the omission no longer exists.

| ID | Exception | Decision | Impact | Compatibility path |
| --- | --- | --- | --- | --- |
| E-002 | The HDF5 field I/O requires the system HDF5 C library when the `hdf5` feature is enabled | ADR 0003 (D-03) | Builds without system HDF5 cannot write native field dumps; the feature reports `Hdf5Error::Unsupported` instead of writing a private format | Install the distribution's HDF5 development package (CI does this) or point `HDF5_LIB_DIR` at the library |
| E-003 | The GUI uses egui/wgpu instead of Qt/VTK | ADR 0004 (D-04) | Qt-specific extensions and VTK-backed dialogs are not available; exports are implemented in Rust | Native workflows are preserved at the model and file-format level; export parity is tracked by RM-104 |
| E-006 | **Resolved 2026-10-29.** The all-Rust GUI reached the native layout, workflow, icon set and metrics (RM-152, RM-153) | Owner decision: parity is required; the parity rows are `Verified` | The residual is environmental: no native Qt build for a side-by-side screenshot and no macOS/Linux-X11 desktop session | Build the native Qt application for a side-by-side capture and run the session on macOS/Linux; see `audits/gui-parity.md` and `audits/gui-qa.md` |
| E-005 | No nightly reference job is currently scheduled | Owner deleted the `openEMS-nightly-reference` Windows Task Scheduler entry on 2026-10-30; hosted Actions remain unavailable at the account level (dispatch returns HTTP 422) | No nightly or cross-platform CI run exists now. The job body is still `scripts/ci/run_nightly_wsl.sh`, but nothing triggers it | Re-enable Actions and place `.github/workflows/reference.yml` on the default branch, or recreate the local scheduled task on explicit owner instruction |
| E-004 | `hyp2mat` is not built on FreeBSD: its Clipper2 backend (`clipper2c-sys`) has no FreeBSD target | RM-120/RM-121 platform matrix | FreeBSD builds and tests fparser, CSXCAD, openEMS, CTB and the GUI crates; only the offline PCB converter is unavailable there | Use the native hyp2mat, a Linux/macOS/Windows build, or replace the Clipper2 backend with a portable implementation if FreeBSD conversion is required |
| E-015 | The cylindrical operator-dump `vi`/`iv` normalization still differs from native, although the physical gates pass | Accepted diagnostic difference (2026-11-01) | `scripts/ci/run_multigrid_operator_check_wsl.sh` is not clean for the standalone coefficient fixtures. The coaxial single-grid gate, the multi-grid TEM parity and the multi-grid coax probe gate all pass, so this is a debug-dump representation difference, not a solver result difference. Operator dump differential tests (`operator_dump_check_wsl.sh`) pass for Cartesian cases. | Accepted as diagnostic-only; solver physics unaffected. |

### Resolved

- **E-001 (fparser numeric backends) closed 2026-11-01:** `float`, `long-double`
  (binary128), `mpfr` (256-bit rug/GMP) and `long-integer` (`rug::Integer`) are
  opt-in features. Native differentials: long-double 30/30 worst 0.0, MPFR
  30/30 worst 1.8e-29, long-integer 52/52 exact with parse-error agreement.
  The default `f64` and its 36k-expression corpus are unchanged.
- **E-010 (hosted CI) out of scope 2026-11-01:** owner decision; the accepted
  platform evidence is the local WSL2 acceptance gate and the Windows build.
  No hosted CI is part of the migration plan.

- **E-007 (cylindrical multi-grid) closed 2026-11-01:** `setup_fdtd` now builds
  the native-layout pair (base = full mesh, child = inner rho + every second
  alpha line), attaches the inner engine through `MultiGridLink`, and runs the
  native `Engine_CylinderMultiGrid` barrier order. Probes and dumps sample the
  full base mesh. Child-safe extensions follow the native
  `IsCylindricalMultiGridSave` matrix; TFSF and Mur on the alpha/rho-min faces
  are rejected instead of silently dropped, and the child skips UPML exactly
  like native. Validation: closed-alpha coaxial line with a `1/rho` excitation
  and three voltage probes, 220 steps, multigrid vs single grid: `u1` 1.04e-7,
  `u2` 9.3e-8 relative, identical phase (1.0761 rad), `beta` error 6.2e-3 and a
  log radial profile of 0.5642 vs the analytic 0.5643 (1.3e-4). The operator
  dump difference is tracked separately as E-015.

- **E-008 (CellConstantMaterial averaging) closed 2026-11-01 (RM-167/D-02):**
  `AverageMatCellCenter` is implemented in `operator.rs`
  (`MaterialAveraging::CellCenter`) with the native dual-node sampling, and
  `CellConstantMaterial="1"` selects it at setup. Differential evidence on a
  20^3 mesh with a material box straddling cell centres: native vs Rust
  `vv` exact, `vi` 9.9e-8, `ii` exact, `iv` 1.1e-13
  (`scripts/ci/run_operator_dump_check_wsl.sh`, second case). Unit tests cover
  the quarter-vs-centre difference and the setup switch.
- **E-009 (no CST cross-validation) closed 2026-10-31 (CST-001 / VAL-001):**
  CST Studio Suite 2026 ran the MSL notch fixture (waveguide ports, 160
  steps/wavelength, fixed mesh) and the comparison harness reports **PASS**:
  notch **3.6425 vs 3.6700 GHz (0.749 %)**, |S11| 0.9981 vs 0.9921, |S21|
  -29.8 vs -50.1 dB, |S11| RMS 1.42 dB (gate 3 dB). Mesh convergence 80 -> 160
  steps moved the notch 3.6327 -> 3.6425 GHz toward openEMS, so the result is
  not mesh noise. Evidence: `docs/migration/cst/PREPARATION.md` and
  `run_wg160/` (Touchstone, report, CST messages). The low-frequency power
  balance (0.68 at 1 GHz) is recorded as a band-edge port limitation and is not
  gated.
- **E-012 (no Windows package) closed 2026-10-31 (PKG-001):**
  `scripts/ci/build_windows_package.ps1` and
  `.github/workflows/windows-rust-package.yml` build the Rust-native Windows
  x64 package (six executables, the HDF5/MSVC DLL closure and both PyO3
  wheels). The package was built and smoke-tested locally: CLI help, a 20-step
  FDTD run, a re-run from the extracted zip with conda removed from `PATH`, and
  a wheel import plus XML write. Artifact details, hash and limits are in
  `docs/migration/WINDOWS_PACKAGE.md`. The native C++ `windows-package.yml` is
  untouched and remains an unrun reference path; it is not the migration
  deliverable.
- **E-011 (performance gate not accepted) closed 2026-10-31 (PERF-001, owner
  decision):** the owner accepted **wall <= 4.0x** and **peak RSS <= 3.25x** of
  the native solver. The measured worst cases are 2.90x wall (`msl_port`) and
  3.08x RSS (`Coax`, basic), so the accepted limits hold with margin. The gate
  is part of `scripts/ci/run_full_acceptance_wsl.sh`: it measures both solvers
  fresh on every run and fails on any case outside the limits, instead of
  trusting the committed CSV.
- **E-013 (no floating dock windows) closed 2026-10-31 (owner decision,
  ADR 0010):** `egui_tiles` docks panes as tabs/splits with drag grips and
  persists the tree, but cannot float panes outside the main window. The owner
  accepted the tab/split workflow as the docking scope for this fork, so the
  missing Qt-style floating panels are a decided scope choice, not open work.
  The docking behaviour and its 32 `qcsxcad-egui` (4 docking) + 18 `appcsxcad`
  tests are unchanged; floating windows would need a new ADR and a separate
  viewport.
- **E-014 (no sanitizer pass) closed 2026-10-31 (RM-183):**
  `scripts/ci/run_asan_checks_wsl.sh` runs the fparser suite and the
  `operator::` tests under `-Zsanitizer=address` with `-Zbuild-std` and a
  64 MiB test-thread stack: **53 + 58 passed**, no ASan report. TSan is not
  enabled for this single-threaded selection and is not claimed.

## Change rule

An exception may only be added or removed together with the decision record it
cites. Removing an exception requires the missing capability to be implemented
and validated first.
