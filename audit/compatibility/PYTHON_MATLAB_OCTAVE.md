# Python, MATLAB and Octave

## Python

| Item | State |
|---|---|
| Packages | `CSXCAD` and `openEMS`, PyO3 extension + Python façade (`CSXCAD/rust-py`, `openEMS/rust-py`) |
| Native suites | `scripts/ci/run_rust_python_tests_wsl.sh`: **405 tests pass** (250 openEMS + 155 CSXCAD); 2 `Test_GPUPlugins` tests reported `SKIPPED: NO GPU BACKEND` (ADR 0002), never passed |
| API compatibility | native class/method names, ownership/wrapper behavior tested by the carried suites; NumPy arrays for grid/model data |
| Fixed in this audit (RM-168) | `SetGaussExcite(..., dc_free=True)`, `_SetLibraryArguments` `RuntimeError` + engine diagnostics, `Write2XML` incomplete-setup refusal, `CSPropDiscMaterial.GetPolyDataModel` NumPy arrays + live transform, empty model on an unreadable file |
| Packaging | wheels built and imported in the WSL venv; Windows/macOS wheels not built in this session |
| Gaps | no wheel matrix for all supported Python versions; no `pip install` from a clean machine outside the venv |

## MATLAB / Octave

| Item | State |
|---|---|
| C ABI | `csxcad-matlab` and `openems-matlab` cdylibs; 34 exported symbols checked by `abi_inventory.rs`; `catch_unwind` on every export; null/deleted-pointer contract tests |
| M-files | 70 CSXCAD + 121 openEMS + 29 CTB `.m` files retained from upstream |
| Octave | unmodified upstream testsuite **10/10** (recorded acceptance); CTB CLI Octave exercise PASS |
| MATLAB | **PASS** (smoke, R2025b/PCWIN64): `InitCSX`/`DefineRectGrid`/`AddMetal`/`AddBox`/`InitFDTD` → `WriteOpenEMS` (XML) → `RunOpenEMS` with `--no-simulation` and a 50-step simulation, both via the Rust CLI. Command: `matlab -batch "run('.../matlab_smoke.m')"` |
| Gaps | MATLAB/Octave binaries are host-specific; this is a Windows MATLAB smoke, not a full MATLAB test suite; interleaved-complex vs legacy array behavior is exercised by the Octave suite on this host |

## Cross-language equivalence

The Python, Octave and CLI paths all drive the same Rust core; the acceptance
runs the same model through the native Python suite, the Octave suite and the
Rust CLI and compares against the native solver. The wrappers do not implement
physics.

## Not claimed

- Python 3.14 is the venv used here; other versions are untested in this
  session.
- MATLAB is verified only at smoke level (model write + setup + short run); the full MATLAB suite is not executed.
