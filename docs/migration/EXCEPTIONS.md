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
| E-006 | Interactive GUI QA is bounded to the Windows desktop and to the automated widget tests: the native Qt side-by-side comparison and the macOS/Linux-X11 platform matrix are not executed | Owner instruction 2026-10-29 (RM-106) | The renderer, editors, undo and exports are covered by tests; visual parity with the native Qt GUI and the non-Windows window managers are not measured | Build native AppCSXCAD with Qt5 and run it next to the port on a desktop; add macOS/Linux X11 runs to the GUI checklist when a host exists |
| E-005 | The nightly reference job runs from Windows Task Scheduler (`openEMS-nightly-reference`, daily 03:00) instead of GitHub Actions | Owner instruction 2026-10-29 (RM-124) | No hosted nightly or cross-platform CI run; the nightly is a Linux/WSL job on this workstation. Push-triggered Actions remain unavailable at the account level (dispatch returns HTTP 422) | Re-enable Actions and place `.github/workflows/reference.yml` on the default branch; the same script (`scripts/ci/run_nightly_wsl.sh`) is the job body, so the switch is a runner change |
| E-004 | `hyp2mat` is not built on FreeBSD: its Clipper2 backend (`clipper2c-sys`) has no FreeBSD target | RM-120/RM-121 platform matrix | FreeBSD builds and tests fparser, CSXCAD, openEMS, CTB and the GUI crates; only the offline PCB converter is unavailable there | Use the native hyp2mat, a Linux/macOS/Windows build, or replace the Clipper2 backend with a portable implementation if FreeBSD conversion is required |

## Change rule

An exception may only be added or removed together with the decision record it
cites. Removing an exception requires the missing capability to be implemented
and validated first.
