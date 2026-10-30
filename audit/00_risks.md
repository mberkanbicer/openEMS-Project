# Ranked risks

Severity follows the protocol: P0 = wrong physics/silent corruption, P1 =
incomplete major function or unverified advertised mode, P2 = maintainability
or validation strength, P3 = future work.

## P0 — silent wrong results (fixed in this audit)

| ID | Risk | Evidence | Status |
|---|---|---|---|
| NUM-001 | `CellConstantMaterial=1` accepted, quarter-cell averaging used anyway | `openEMS/rust/src/openems.rs` stores the flag; `operator.rs` only implements `AverageMatQuarterCell`; native `FDTD/operator.h:149` switches to `CentralCell` | **FIXED**: setup now refuses the option (E-008) with `cell_constant_material_is_rejected_at_setup` |
| NUM-002 | `MultiGrid` accepted/stored/exposed but never used; RM-061 claimed Verified without evidence | `fdtd_options.rs`, `openems.rs::set_multi_grid`; no multigrid code in operator/engine; no exception | **FIXED**: setup and `set_multi_grid` refuse it (E-007); tests added; RM-061 evidence corrected |

Residual risk: other upstream attributes could be parsed and ignored in the
same way. The audit checked every `FdtdOptions` field: after these two, the rest
reach the operator/engine or the writer.

## P1 — advertised capability or evidence

| ID | Risk | Evidence | Next |
|---|---|---|---|
| CI-001 | No hosted run at this HEAD; macOS/FreeBSD/Windows claims rest on a pre-`f69ed4d` run | E-005; Actions disabled | enable Actions at account level or publish the limitation |
| REC-001 | E-005 describes a nightly task the owner deleted; no nightly runs now | `EXCEPTIONS.md` E-005 | corrected in this audit |
| REC-002 | `FINAL_AUDIT.md` headline counts are stale (96/53 vs 166/0) | `FINAL_AUDIT.md` | re-issue or point to the register |
| PY-001 | Python façade drifted from the carried upstream tests (`dc_free`, engine diagnostics, `Write2XML` completeness) | acceptance log `python_suites.log` (3 failures, 3 errors) | **FIXED** in RM-168; rebuild + rerun required |
| PKG-001 | Windows installer workflow has no recorded run at this HEAD | `.github/workflows/windows-package.yml` | run it or mark unverified |

## P2 — validation strength and product polish

| ID | Risk | Evidence | Next |
|---|---|---|---|
| VAL-001 | Independent validation is partly covered: cavity TE101 converges at order 2.05/2.03; slab, MSL and dt refinement are still missing | `audit/numerics/CONVERGENCE.md` | slab/MSL/dt refinement |
| PERF-001 | Baseline without an accepted threshold | 3.78x/2.14x/2.92x wall; no gate | agree per-case gate |
| GUI-001 | sRGB material colours render too light | `audits/gui-modernization-audit.md` §9 | linearise vertex colours |
| GUI-002 | Panel sizes do not persist | egui panel state is session-only | persist with settings |
| DOC-001 | No rustfmt/clippy baseline | `cargo fmt --check` fails on pre-existing code | separate cleanup PR |

## P3 / accepted scope

- GPU compute: not implemented, excluded by ADR 0002.
- FreeBSD hyp2mat: excluded by E-004.
- fparser extended precision: excluded by E-001/ADR 0006.
- Multi-grid implementation: feature, not a patch; E-007 keeps the limitation
  explicit until then.

## Execution order

1. NUM-001/NUM-002 guards + tests (done; rerun the solver suite).
2. PY-001 rebuild and native Python suites (in progress).
3. Records E-005/FINAL_AUDIT (E-005 corrected; FINAL_AUDIT to re-issue).
4. Validation: analytic SAR, convergence study, performance gate.
5. GUI colour management and layout persistence.
6. Platform matrix when Actions or hosts are available.
