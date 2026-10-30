# Completion dashboard

Audit of the **existing** Rust port. Basis: `component_matrix.csv` (47
subsystem rows) plus the executed commands in `00_baseline.md`. This is not a
file-count percentage; 34 of 47 audited subsystems have executed verification
evidence, but the two P0 rows below mean the register's "169 Verified" tally
overstates correctness for the affected input classes.

## 1. Status counts (subsystem level)

| Status | Count | Meaning here |
|---|---:|---|
| `VERIFIED_COMPLETE` | 34 | implementation + executed comparison/analytic result recorded |
| `IMPLEMENTED_UNVERIFIED` | 1 | Windows installer workflow; no run at this HEAD |
| `IMPLEMENTED_BROKEN` | 1 | viewport colour management (GUI-001) |
| `PARTIAL` | 3 | performance threshold, convergence study, dock-layout persistence |
| `INTENTIONALLY_DIFFERENT` | 1 | fparser extended-precision variants (E-001/ADR 0006) |
| `INTENTIONALLY_UNSUPPORTED` | 5 | GPU compute (ADR 0002), FreeBSD hyp2mat (E-004), GUI solver control, multi-grid (E-007), cell-constant material (E-008) |
| `BLOCKED` | 2 | hosted CI/platform matrix (E-005), CST comparison (no data) |
| **Total** | **47** | |

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
| PKG-001 | `windows-package.yml` is present but has no recorded run at this HEAD. | workflow file, no artefact | Run it or mark `IMPLEMENTED_UNVERIFIED` |

## 4. P2 — validation strength, performance, GUI

| ID | Finding | Evidence | Next action |
|---|---|---|---|
| VAL-001 | Independent validation was thin; the cavity is now covered. Two analytic wave-speed tests plus native-parity cases, and a **cavity TE101 refinement study (order 2.05/2.03)**; slab, MSL and dt refinement still missing, no CST data. | `audit/numerics/CONVERGENCE.md`; `reference-data/convergence/cavity.json` | Add slab, MSL notch and dt refinement |
| PERF-001 | Baseline exists (wall 3.78x / 2.14x / 2.92x native; RSS 0.32x / 2.96x / 0.39x) but no accepted threshold. | `reference-data/perf/performance-baseline.md` | Agree per-case gate: median of 5, ≤4x wall, ≤20 % regression, RSS ≤3.25x or absolute cap |
| GUI-001 | Materials render lighter than native because stored sRGB colours are written as linear on an sRGB surface. | `audits/gui-modernization-audit.md` §9 | Linearise vertex colours; visual + numeric check on one fixture |
| GUI-002 | Theme persists; panel sizes/layout do not (egui panel state is session-only). | `qcsxcad-egui/src/app.rs` | Persist panel geometry with the settings file |
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
3. **P2 validation:** analytic SAR, convergence study, then the performance
   gate. Each needs its own recorded run.
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
