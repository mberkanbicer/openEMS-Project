# Exception register (RM-126)

Approved, bounded omissions from the native feature set. Every entry needs an
impact statement, an owner decision and a native-compatibility path. Anything
not listed here is an open task, not an accepted exception.

The former E-002 ("`ctb-rs` has no standalone binary") was removed on
2026-10-27: RM-116 delivered the `ctb` command (`info`, `convert`, `renorm`)
with M-file wrappers, so the omission no longer exists.

| ID | Exception | Decision | Impact | Compatibility path |
| --- | --- | --- | --- | --- |
| E-001 | fparser numeric variants (`float`, `long double`, long integer, MPFR/GMP) are not ported; only `f64` is maintained | ADR 0006 (D-06) | Scripts that rely on extended precision or MPFR/GMP evaluate in `f64`. The openEMS solver and CSXCAD use `f64` in the reference build, so solver results are unaffected | A consumer that needs another precision requires a new decision; the native C++ parser remains available for differential checks |
| E-002 | The HDF5 field I/O requires the system HDF5 C library when the `hdf5` feature is enabled | ADR 0003 (D-03) | Builds without system HDF5 cannot write native field dumps; the feature reports `Hdf5Error::Unsupported` instead of writing a private format | Install the distribution's HDF5 development package (CI does this) or point `HDF5_LIB_DIR` at the library |
| E-003 | The GUI uses egui/wgpu instead of Qt/VTK | ADR 0004 (D-04) | Qt-specific extensions and VTK-backed dialogs are not available; exports are implemented in Rust | Native workflows are preserved at the model and file-format level; export parity is tracked by RM-104 |
| E-006 | **Resolved 2026-10-29.** The all-Rust GUI reached the native layout, workflow, icon set and metrics (RM-152, RM-153) | Owner decision: parity is required; the parity rows are `Verified` | The residual is environmental: no native Qt build for a side-by-side screenshot and no macOS/Linux-X11 desktop session | Build the native Qt application for a side-by-side capture and run the session on macOS/Linux; see `audits/gui-parity.md` and `audits/gui-qa.md` |
| E-005 | No nightly reference job is currently scheduled | Owner deleted the `openEMS-nightly-reference` Windows Task Scheduler entry on 2026-10-30; hosted Actions remain unavailable at the account level (dispatch returns HTTP 422) | No nightly or cross-platform CI run exists now. The job body is still `scripts/ci/run_nightly_wsl.sh`, but nothing triggers it | Re-enable Actions and place `.github/workflows/reference.yml` on the default branch, or recreate the local scheduled task on explicit owner instruction |
| E-004 | `hyp2mat` is not built on FreeBSD: its Clipper2 backend (`clipper2c-sys`) has no FreeBSD target | RM-120/RM-121 platform matrix | FreeBSD builds and tests fparser, CSXCAD, openEMS, CTB and the GUI crates; only the offline PCB converter is unavailable there | Use the native hyp2mat, a Linux/macOS/Windows build, or replace the Clipper2 backend with a portable implementation if FreeBSD conversion is required |
| E-007 | Cylindrical multi-grid (`MultiGrid`) is not implemented | Owner decision 2026-10-30 (RM-061/D-02: implement or fail loudly) | `set_multi_grid` / Python `SetMultiGrid` keeps the native setter contract (validate and store), but `setup_fdtd` refuses a model with radii: it stops with an explicit error instead of silently running as a single-grid model | Use the native solver for multi-grid models, or implement the cylindrical multi-grid operator/engine and remove this exception |
| E-008 | `CellConstantMaterial` (cell-centre material probing) is not implemented | Owner decision 2026-10-30 (RM-167/D-02) | A model that sets `CellConstantMaterial` stops in `setup_fdtd` with an explicit error; the port only implements native `AverageMatQuarterCell` | Implement `AverageMatCellCenter` with a differential fixture and remove this exception |

## Change rule

An exception may only be added or removed together with the decision record it
cites. Removing an exception requires the missing capability to be implemented
and validated first.
