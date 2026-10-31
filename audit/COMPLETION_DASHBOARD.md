# Completion dashboard

Audit of the **existing** Rust port. Basis: `component_matrix.csv` (49
subsystem rows) plus the executed commands in `00_baseline.md`. This is not a
file-count percentage; 39 of 49 audited subsystems have executed verification
evidence, consistent with the register's **179 `Verified`** rows.

## 1. Status counts (subsystem level)

| Status | Count | Meaning here |
|---|---:|---|
| `VERIFIED_COMPLETE` | 39 | implementation + executed comparison/analytic result recorded |
| `IMPLEMENTED_UNVERIFIED` | 1 | Windows installer workflow; no run at this HEAD (E-012) |
| `PARTIAL` | 1 | performance threshold (E-011) |
| `INTENTIONALLY_DIFFERENT` | 1 | fparser extended-precision variants (E-001/ADR 0006) |
| `INTENTIONALLY_UNSUPPORTED` | 5 | GPU compute (ADR 0002), FreeBSD hyp2mat (E-004), GUI solver control, multi-grid (E-007), cell-constant material (E-008) |
| `BLOCKED` | 2 | hosted CI/platform matrix (E-010), CST comparison (E-009) |
| **Total** | **49** | |

Trust level: high for the default Cartesian/homogeneous/differential paths
(51-case native harness + analytic wave-speed + Octave/Python suites). Models
that set `CellConstantMaterial` or `MultiGrid` now stop with an explicit setup
error (E-007/E-008) instead of silently simulating something else. No CST or
convergence evidence exists.

## 2. P0 — silent wrong physics (fixed in this audit)

### NUM-001 — `CellConstantMaterial` is accepted and ignored

- Upstream: `openEMS/openems.cpp:1007` parses it; `FDTD/operator.h:149`
  switches material averaging to `CentralCell` (material probed at the cell
  centre).
- Rust: `openEMS/rust/src/openems.rs` parses and stores
  `cell_constant_material` (CLI/Python/MATLAB expose `SetCellConstantMaterial`);
  `openEMS/rust/src/operator.rs` implements only `AverageMatQuarterCell`
  (lines 709/892/927/2371) and never reads the flag.
- Effect: a model that requests cell-constant materials silently simulates
  quarter-cell-averaged materials, i.e. different ε/κ/μ/σ at material
  interfaces. Default models (QuarterCell) are unaffected.
- Evidence: code search, no test covers the flag. Taxonomy
  `IMPLEMENTED_BROKEN`.
- Disposition: **fixed** by rejecting the option at setup with an explicit
  error (E-008) and `cell_constant_material_is_rejected_at_setup`. Implementing
  `AverageMatCellCenter` remains a feature for a later change.

### NUM-002 — cylindrical `MultiGrid` is accepted, stored, exposed and ignored

- Upstream: `FDTD/operator_cylinder*`, `engine_cylinder*`,
  `*cylindermultigrid*` implement nested cylindrical grids.
- Rust: `fdtd_options.rs` parses `MultiGrid`, `openems.rs` stores it and
  exposes `set_multi_grid` (Python `SetMultiGrid`, MATLAB C-ABI), but the
  radii never reach `setup_fdtd`, the operator or the engine. There is no
  multigrid code and no exception entry.
- Register defect: RM-061 is marked `Verified` with the evidence cell
  containing only the row title ("Either analytic cylinder case or explicit
  error + exception") — no command, no result, no exception. This violates
  `STATUS_POLICY.md` rules 1 and 6.
- Effect: a multigrid model runs as a single-grid cylindrical model, silently.
- Taxonomy `IMPLEMENTED_BROKEN`.
- Disposition: **fixed** by rejecting radii in `setup_fdtd` while keeping the
  native setter contract (E-007), correcting RM-061, and adding two regression
  tests. Implementing multigrid is a separate L feature.

## 3. P1 — evidence and platform claims

| ID | Finding | Evidence | Next action |
|---|---|---|---|
| REC-001 | E-005 still describes the nightly Windows task as installed; the owner deleted it on 2026-10-30, so no nightly runs now. Hosted Actions remain disabled. | `docs/migration/EXCEPTIONS.md` E-005 | Correct E-005; state "no nightly scheduled"; keep the script as the job body |
| REC-002 | `FINAL_AUDIT.md` header still reports 96 Verified / 53 Implemented although the register is 166/0/0; it carries later notes but the headline is stale. | `docs/migration/FINAL_AUDIT.md` | Re-issue the final audit against this HEAD or point it at the register as the only count |
| CI-001 | No hosted run exists at this HEAD; macOS/FreeBSD/Windows claims rest on a pre-`f69ed4d` run. | E-005, `.github/workflows` | Enable Actions at account level, or publish the platform limitation in the release note |
| PKG-001 | **FIXED 2026-10-31:** Rust-native Windows package built and smoke-tested (`WINDOWS_PACKAGE.md`); native C++ workflow untouched, reference-only. | `scripts/ci/build_windows_package.ps1`; `dist/*.zip` (ignored); `WINDOWS_PACKAGE.md` | none |

## 4. P2 — validation strength, performance, GUI

| ID | Finding | Evidence | Next action |
|---|---|---|---|
| VAL-001 | Independent validation is now broad: analytic wave-speed tests, a **cavity TE101 mesh study (2.05/2.03)**, a **time-step study (2.32 vs the dt->0 limit)**, a monotone dielectric speed study, a **converged MSL notch (3.6700 GHz, 3.0e-4 spread)** and an **analytic SAR lossy line (9.4e-4)**. No CST data and no SAR-averaging convergence claim. | `audit/numerics/CONVERGENCE.md`; `reference-data/convergence/` | CST data when available |
| PERF-001 | **FIXED 2026-10-31:** owner accepted wall <=4.0x / RSS <=3.25x; the acceptance run measures both solvers fresh and enforces the limits (worst recorded 2.90x/3.08x). | udit/performance/CPU_BASELINE.md; scripts/ci/check_performance_baseline.py; scripts/ci/run_full_acceptance_wsl.sh | none |
| DOC-001 | The repository is hand-formatted; `cargo fmt --check` fails on pre-existing code, and clippy has no baseline. | `00_baseline.md` §3 | Separate formatting PR; establish clippy baseline |

## 5. Working code that must not be disturbed

- Operator/engine numerics, EC coefficients, CFL, UPML/Mur, excitations,
  dispersive ADE, conducting sheets, lumped ports, steady state, cylindrical
  r=0/seam.
- Probes/DFT/end criteria, HDF5/VTK writers, NF2FF, SAR processing.
- CSXCAD model/XML/materials/grid/parameters, fparser f64, hyp2mat, CTB.
- Python/MATLAB/Octave surfaces and the install layout.
- GUI editor workflow (tree/inspector/viewport/exports) and its theme layer.

No module above is to be replaced while closing the two P0 rows.

## 6. Dependency-aware fix order

1. **P0 correctness (this change):** NUM-001, NUM-002 — fail loudly, record
   exceptions, correct RM-061, add regression tests. Re-run the solver suite.
2. **P1 records/platform:** REC-001, REC-002, CI-001/PKG-001. No code risk.
3. **P2 validation:** convergence study, then the performance gate (analytic SAR
   done, RM-178). Each needs its own recorded run.
4. **P2 GUI:** colour management, layout persistence.
5. **Deferred/blocked:** CST (no data), GPU (scope), multi-grid implementation
   (feature, not a patch), macOS/FreeBSD desktop sessions.

## 7. No-change decisions

- Do not re-port solver kernels that already match native within recorded
  bounds.
- Do not replace the egui/wgpu GUI (ADR 0004/E-003); the DESIGN.md redesign is
  presentation-only and preserves the renderer.
- Do not introduce a GPU backend to "complete" a scope that ADR 0002 excludes.
- Do not change fparser precision (E-001) or the MATLAB/Python ABI without a
  compatibility decision.

## 8. Must not be portrayed as finished

- Any multigrid or cell-constant-material model result (currently silent).
- CST equivalence (no data).
- GPU acceleration (not implemented; out of scope).
- macOS/FreeBSD desktop verification at this HEAD.
- A performance "pass" (only a baseline).
