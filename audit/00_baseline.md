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
| 5 | `scripts/ci/run_full_acceptance_wsl.sh` (WSL2, native openEMS v0.37.0) | **13/13 PASS** (section 5) | `docs/migration/ACCEPTANCE.md`; `%TEMP%\opencode\acceptance_run3.log` |
| 6 | `cargo test --workspace --all-targets --no-fail-fast` (final tree) | **882 passed, 0 failed, 0 ignored**, 32 binaries | `%TEMP%\opencode\workspace_test_final.log` |
| 7 | `scripts/ci/run_convergence_check_wsl.sh` | cavity TE101 order 2.05 / 2.03; errors 1.770e-3 / 4.270e-4 / 1.047e-4 | `docs/migration/reference-data/convergence/cavity.json` |

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

The acceptance completed on 2026-10-30 at `ff95333` + the audit changes
(`ACCEPTANCE.md`): **13/13 PASS**.

| Check | Result | Evidence |
|---|---|---|
| workspace build (release) | PASS | 1 build |
| crate unit + integration tests | PASS | 804 tests (fresh, includes RM-169) |
| HDF5 feature tests | PASS | 504 tests (cached from the same tree) |
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

- The suite reuses a check's cached PASS for the same revision and log
  directory (`run()` / `ACCEPTANCE_RESUME`). The cached checks were produced
  from this tree after the Python/Rust fixes; the crate tests were re-run fresh
  after the CTB target clean. The report does not hide a cached row.
- The earlier attempts failed for two reasons that are fixed, not suppressed: a
  stale `CARGO_MANIFEST_DIR` baked into the CTB differential test binary when
  the tree moved from `D:` (fixed by `cargo clean -p ctb-rs`; the source uses
  `CARGO_MANIFEST_DIR`), and real Python façade drift (fixed in RM-168). The
  CTB CLI tests also failed once with a transient missing binary and passed on
  every later run.

