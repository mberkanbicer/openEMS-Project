# Baseline — commands executed for this audit

All commands ran in `C:\Users\mberkanbicer\Projects\openEMS-Project-rust` with
`HDF5_LIB_DIR` and `PATH` pointing at the local HDF5 runtime. Dates: 2026-10-30.

## 1. Executed in this session

| # | Command | Result | Evidence |
|---|---|---|---|
| 1 | `cargo test --workspace --all-targets --no-fail-fast` | **851 passed, 0 failed, 0 ignored**, 30 test binaries | `%TEMP%\opencode\workspace_test.log` |
| 2 | `cargo check --workspace` | pass; only pre-existing `unused_variables` warnings in `openEMS/rust/src/{debug_dump,openems}.rs` | shell output |
| 3 | `python scripts/ci/check_migration_docs.py` | `migration record check passed` | shell output |
| 4 | `cargo test -p qcsxcad-core -p qcsxcad-egui -p appcsxcad` | 52 + 24 + 13 passed | subset of #1, run separately |
| 5 | `scripts/ci/run_full_acceptance_wsl.sh` (WSL2, native openEMS v0.37.0) | **13/13 PASS** (section 5) | `docs/migration/ACCEPTANCE.md`; `scripts/ci/run_full_acceptance_wsl.sh (report: docs/migration/ACCEPTANCE.md)` |
| 6 | `cargo test --workspace --all-targets --no-fail-fast` (final tree) | **886 passed, 0 failed, 0 ignored**, 33 binaries | `%TEMP%\opencode\workspace_test_final.log` |
| 7 | `scripts/ci/run_convergence_check_wsl.sh` | cavity TE101 order 2.05 / 2.03; errors 1.770e-3 / 4.270e-4 / 1.047e-4 | `docs/migration/reference-data/convergence/cavity.json` |
| 8 | `cargo run --release -p openems-core --example dielectric_convergence` | dielectric speed errors 2.14e-3 / 1.15e-3 / 9.25e-4; order 0.90 / 0.31, estimator-limited | `docs/migration/reference-data/convergence/dielectric.json` |
| 9 | `matlab -batch "run(...matlab_smoke.m)"` (R2025b, Windows) | XML write, `--no-simulation` setup and 50-step run through the Rust CLI all returned; `MATLAB smoke: PASS` | `scripts/ci/matlab_smoke.m` |
| 10 | `scripts/ci/msl_convergence.py` | no interior S11 notch in 1-7 GHz (band-edge minimum 0.085-0.089); inconclusive, no order | `docs/migration/reference-data/convergence/msl_notch.json` |
| 11 | `scripts/ci/convergence_study.py --mode dt` | phase estimator at 400 ns: temporal error 2.06 MHz -> 0.41 MHz vs the dt->0 limit (order 2.32); 3.73 MHz residual is spatial | `docs/migration/reference-data/convergence/cavity_dt.json` |
| 12 | `scripts/ci/run_analytic_sar_check_wsl.sh` | lossy line 2 GHz: alpha 9.3513 vs 9.3601 Np/m (9.4e-4), beta 84.3651 vs 84.3547 rad/m (1.2e-4), SAR slope 18.7027 vs 18.7202 1/m (9.4e-4), formula 1.7e-7 | `docs/migration/reference-data/convergence/analytic_sar.json` |
| 13 | `scripts/ci/run_msl_convergence_wsl.sh` | MSL notch (\|S11\| peak / \|S21\| dip): 3.6700 / 3.6712 / 3.6703 GHz at 373/448/560 um, spread 3.0e-4; quarter-wave 3.6871 GHz (0.46%) | `docs/migration/reference-data/convergence/msl_notch.json` |
| 14 | `scripts/ci/run_miri_checks_wsl.sh` | Miri: fparser 21 passed / 0 failed (32 optimizer FP tests filtered), openems-core 3 operator tests passed; no UB | `%TEMP%\opencode\miri_all2.log` |
| 15 | `cargo test -p qcsxcad-egui --features docking` / `cargo test -p appcsxcad` | 32 + 18 passed (4 docking tests); default and tabbed layouts captured | `docs/migration/audits/gui-docking-1440.png`, `gui-docking-docked-1440.png` |

The workspace test run used default features. The HDF5 feature suite is a
separate run inside the acceptance script (475 tests at the last recorded
revision).

## 2. Recorded baseline (not re-run in this session)

| Evidence | Revision | Result |
|---|---|---|
| Full acceptance, 13 checks | `cce4905` (recorded in `docs/migration/ACCEPTANCE.md`) | 13/13 PASS: release build, 764 crate tests, 475 HDF5 tests, 2 Python packages, 448 native Python cases, Octave 10/10, 51 differential cases, cylindrical SAR, curve excitation, CTB Octave, install layout, records, placeholders |
| Performance | refreshed at `c54f55d` (3 runs, SHA-256 pinned) | default: cavity 2.45x, Coax 2.23x, msl_port 2.90x; basic: 1.61x / 1.67x / 1.65x; RSS 0.32-3.08x. Proposed 4.0x/3.25x gate: PASS. `docs/migration/reference-data/perf/performance-baseline.md` |
| Platform builds | `f69ed4d` | Linux/macOS/FreeBSD/Windows jobs green before Actions was disabled; no run after that revision |

## 3. Commands deliberately not run

| Command | Reason |
|---|---|
| `cargo clippy -- -D warnings` | no clippy baseline; would mix existing warnings with audit changes. Recorded as a P3 cleanup item. |
| `cargo fmt --all -- --check` | the repository is hand-formatted; the check reports diffs in pre-existing code (e.g. `menu_item` signature layout). Running `cargo fmt` would reformat unrelated numerical code. |
| `cargo +nightly miri`, ASan/TSan, `cargo fuzz` | not installed/configured; no fuzz corpus exists. Recorded as a testing gap, not a pass. |
| CST comparison | no CST licence, project files or exported results exist in the workspace; 0 files reference CST. Status `BLOCKED`, see `cst/`. |
| GPU parity | no GPU compute backend exists (scope decision, ADR 0002). Status `INTENTIONALLY_UNSUPPORTED`. |
| macOS/FreeBSD desktop sessions | no such host is available here. Status `BLOCKED`; the last recorded run predates the current HEAD. |

## 4. Toolchain / environment

```
rustc 1.99.1 (58cf8f9c3 2026-10-13)
cargo 1.99.1 (5f94df4 2026-08-27)
Windows 11 x86_64 (MSVC), i9-13900H, 48 GB
WSL2 Ubuntu, native openEMS v0.37.0 at ~/opt/openEMS, Octave, Python 3
```

## 5. Acceptance run update

When the background acceptance run finishes, this section is replaced with its
13-row table and the report path. A failure is recorded as FAIL; a check that
cannot run is recorded with its blocker, never as a pass.

The acceptance completed on 2026-10-30 with a clean worktree (the provenance
check now compares with the Windows `core.autocrlf=true` checkout policy),
every check executed fresh in a new log directory. `ACCEPTANCE.md` pins the
full tested SHA and the per-check counts: **13/13 PASS**.

| Check | Result | Evidence |
|---|---|---|
| workspace build (release) | PASS | 1 build |
| crate unit + integration tests | PASS | see `ACCEPTANCE.md` (fresh; includes RM-169..RM-177) |
| HDF5 feature tests | PASS | 506 tests (fresh) |
| Python packages build + imports | PASS | 2 packages |
| native Python suites | PASS | 459 cases; **SKIPPED: 2 GPU plugin tests** (no GPU engine; ADR 0002) |
| native Octave testsuite | PASS | 10 passed, 0 failed, 0 errors |
| differential reference harness | PASS | 51 cases ok |
| cylindrical SAR differential | PASS | per-cell 2.6e-3 (bound 1e-2), peak 1e-3 |
| curve-excitation differential | PASS | peak 4.753e-5, max sample 1.617e-4 |
| CTB Octave delivery | PASS | exercise PASS |
| CMake install layout | PASS | AppCSXCAD ctb hyp2mat nf2ff openEMS sar_calc |
| migration records | PASS | check passed |
| placeholder policy | PASS | self-test passed |

Two notes on honesty:

- This run used a new log directory for `cf3d226`, so no check was served from
  an older revision's cache. The report pins the full tested SHA and states that
  the worktree was clean at startup.
- The earlier attempts failed for two reasons that are fixed, not suppressed: a
  stale `CARGO_MANIFEST_DIR` baked into the CTB differential test binary when
  the tree moved from `D:` (fixed by `cargo clean -p ctb-rs`; the source uses
  `CARGO_MANIFEST_DIR`), and real Python façade drift (fixed in RM-168). The
  CTB CLI tests also failed once with a transient missing binary and passed on
  every later run.

