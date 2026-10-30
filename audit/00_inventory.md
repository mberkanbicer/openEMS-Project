# Phase 0 inventory — existing Rust workspace

Snapshot: 2026-10-30. Read-only phase; no source was modified to produce this
file.

## 1. Repository state

| Item | Value |
|---|---|
| Workspace root | `C:\Users\mberkanbicer\Projects\openEMS-Project-rust` |
| Git root | same (meta-repository fork) |
| Branch | `mberkanbicer-rust-migration-audit` |
| HEAD | `ff95333e2b93c943038d28bf169adca1404fb9e8` (`docs(gui): Precision Workbench audit…`) |
| Remote | `origin https://github.com/mberkanbicer/openEMS-Project.git` (fork; upstream not configured as a push target) |
| Worktree state | clean apart from the untracked `audit/` tree created by this protocol |
| Line endings | Windows `core.autocrlf` makes `git status` inside WSL report every file modified; the Windows worktree is the authoritative one and is clean |

Submodule pointers (current, ahead of the prompt's 2026-10-30 snapshot):

| Component | Current | Prompt baseline | Delta |
|---|---|---|---|
| openEMS | `04dc908324bf64f88709b951be1b7c580de592bc` (v0.37.0-109) | `d686f1df` | + upstream ports recorded in `docs/migration/audits/upstream-sync-2026-10-30.md` |
| CSXCAD | `37f2db9dee6888966f0eb58cf24b48fe32a0b395` (v0.7.0-33) | `626b99f2` | drawing tolerance, polyhedron f64, black edge, nested structure |
| QCSXCAD | `069a45e09961eace8de148cd9c7e4af632928154` (v0.7.0-27) | `6a22e41e` | Precision Workbench GUI |
| AppCSXCAD | `83dee98ade72faf86be4f17652024cdc7b8f727f` (v0.7.0-20) | `bcbc0ad0` | command strip/View menu/theme persistence |
| fparser | `525f4b7f5203ce680b3c460205d2617d3ccdd4c9` | `4b9c845b` | upstream branch merge |
| hyp2mat | `ded44d00b42783f1e77656acbf85a373e884557d` (v0.0.17-9) | `b15f7498` | upstream branch merge |
| CTB | `570847c5eb7e6ba9e7a5479a08b452cdcb16db25` (master-5) | `5ac29367` | upstream branch merge |

The submodules still contain the upstream C/C++ sources (kept as the reference
implementation, per `AGENTS.md` §4). They are **not** linked into the Rust
binaries; see `legacy_dependency_register.md`.

## 2. Toolchain and host

| Item | Value |
|---|---|
| rustc | 1.99.1 (58cf8f9c3 2026-10-13), stable |
| cargo | 1.99.1 (5f94df4 2026-08-27) |
| Edition | workspace crates use edition 2021/2024 (per-crate `Cargo.toml`) |
| Host | Windows 11 x86_64 (MSVC), 13th Gen Intel i9-13900H, 48 GB RAM |
| Secondary | WSL2 Ubuntu, kernel 6.18.54.1, native openEMS v0.37.0 installed at `~/opt/openEMS`, Octave and Python 3 available |
| Native libs | HDF5 (feature-gated), wgpu/winit system drivers; no CUDA/HIP used by the Rust code |

## 3. Workspace packages (15)

| Package | Path | ~Rust LOC | Responsibility |
|---|---|---:|---|
| `fparser-rs` | `fparser/rust` | 4.5k | expression grammar/evaluation (f64 only, E-001) |
| `csxcad-core` | `CSXCAD/rust` | 18.5k | geometry model, grid, materials, parameters, transforms, XML, HDF5, polyhedra |
| `csxcad-python` | `CSXCAD/rust-py` | 3.3k | PyO3 `CSXCAD` package |
| `csxcad-matlab` | `CSXCAD/rust-matlab` | 0.6k | C-ABI cdylib for the M-files |
| `openems-core` | `openEMS/rust` | 27.2k | FDTD operator/engine/extensions, probes/DFT, HDF5, NF2FF, SAR, processing |
| `openems-cli` | `openEMS/rust-cli` | 0.3k | native-named CLI entry point |
| `nf2ff-cli` | `openEMS/nf2ff-cli` | 0.2k | near-to-far-field tool |
| `sar-cli` | `openEMS/sar-cli` | 0.1k | SAR tool |
| `openems-py` | `openEMS/rust-py` | 0.5k | PyO3 `openEMS` package |
| `openems-matlab` | `openEMS/rust-matlab` | 1.6k | C-ABI cdylib, 34 exports |
| `qcsxcad-core` | `QCSXCAD/rust` | 3.9k | document/project, tessellation, export, rendering model, tree/widget traits |
| `qcsxcad-egui` | `QCSXCAD/rust-egui` | 5.2k | egui/wgpu 3D editor, theme, docks |
| `appcsxcad` | `AppCSXCAD/rust` | 1.5k | standalone desktop application |
| `hyp2mat-rs` | `hyp2mat/rust` | 9.1k | HyperLynx/PCB import and CSXCAD conversion |
| `ctb-rs` | `CTB/rust` | 4.6k | S/Y/Z/ABCD networks, Touchstone, reference impedance |

Total Rust source ≈ **81k lines**. The workspace has no generated Rust code.

## 4. Tests that exist

- 32 test binaries in the final debug run of this session (unit +
  integration + doc/bin targets), **881 passed / 0 failed / 0 ignored**; the
  pre-audit run was 851/30. Evidence: section 4 of `00_baseline.md`,
  `workspace_test.log` and `workspace_test_final.log`.
- Integration suites: `CSXCAD/rust/tests` (expression evaluation, mesh
  fixtures, native model parity, ownership contracts, performance baseline,
  transform/parameter parity, XML native corpus), `openEMS/rust/tests/analytic_validation.rs`,
  `openEMS/rust-cli/tests/cli_contract.rs`, `hyp2mat/rust/tests` (CLI and
  fixtures), `CTB/rust/tests` (CLI and differential), plus crate-local unit
  tests (GUI included).
- Recorded acceptance evidence (not re-run before this file was written; the
  current run is tracked in `00_baseline.md`): 13/13 checks including 51
  differential cases, 448 native Python cases, the unmodified Octave testsuite
  10/10, the cylindrical SAR gate and the curve-excitation gate.
- No `#[ignore]` tests anywhere.
- Placeholder scan: no `todo!`, `unimplemented!`, `FIXME` or "not implemented"
  in production Rust; the only match is a test named
  `structure_primitive_type_query_matches_native_unimplemented_stub`, which
  asserts a native stub's behavior. The CI placeholder gate
  (`scripts/ci/check_placeholders.py`) passes.

## 5. GUI, bindings, formats, CI

| Surface | Present |
|---|---|
| GUI | `qcsxcad-egui` + `appcsxcad`: egui 0.37, wgpu 30, winit 0.30; tree/grid/parameter docks, property/primitive/transform editors, 3D viewport, picking, drag tools, exports, undo/redo, dark/light/high-contrast themes, command strip and status bar |
| Solver in GUI | **no** — the desktop app is the geometry/structure editor, as the native AppCSXCAD is; simulation runs through the CLI/Python/Octave |
| Python | PyO3 wheels `CSXCAD` and `openEMS` (`CSXCAD/rust-py`, `openEMS/rust-py`), native-compatible class/method surface |
| MATLAB/Octave | C-ABI cdylibs (`csxcad-matlab`, `openems-matlab`) plus 70 CSXCAD `.m`, 121 openEMS `.m`, 29 CTB `.m` files |
| CLI | `openEMS`, `nf2ff`, `sar_calc`, `ctb`, `hyp2mat`, `AppCSXCAD` installed names |
| Formats | CSXCAD XML, HDF5 fields/probes/SAR/NF2FF, VTK (`.vtr/.vts/.vtp`), Touchstone, STL/PLY/POV/X3D, HyperLynx PCB |
| CI definitions | 4 workflows (`ci.yml`, `rust.yml`, `reference.yml`, `windows-package.yml`) + 35 local scripts under `scripts/ci` |
| CI execution | hosted Actions are disabled at the account level (E-005); the nightly Windows task was deleted by the owner on 2026-10-30, so **no nightly is scheduled now** |
| Records | `docs/migration/` (register with 166 `Verified`, validation, tolerances, acceptance, exceptions, ADRs, per-component audits) |

## 6. What the inventory establishes

The workspace is a substantial, compiling, tested implementation of all seven
components, not a skeleton. The audit therefore focuses on:

1. options and behaviours that are **accepted but not applied** (proven below),
2. claims whose evidence is unit-level or stale,
3. scientific validation gaps (convergence, independent reference data),
4. platform/CI and release claims that the host cannot prove.

Those are enumerated in `COMPLETION_DASHBOARD.md`; they are not assumptions
from an upstream feature list.
