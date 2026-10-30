# Rust port audit — completion protocol deliverables

This tree is the audit asked for by `OPENEMS_RUST_AUDIT_AND_COMPLETION_PROMPT.md`
(2026-10-30). It audits the **existing** Rust implementation first; it does not
re-port working modules and does not treat the prior migration records as proof.

- Workspace: `C:\Users\mberkanbicer\Projects\openEMS-Project-rust`
  (branch `mberkanbicer-rust-migration-audit`).
- Evidence rule: every status names a re-runnable command or an artefact. A
  recorded result that was **not** re-run in this session says so.
- The prompt's taxonomy (`VERIFIED_COMPLETE`, `IMPLEMENTED_UNVERIFIED`,
  `IMPLEMENTED_BROKEN`, `PARTIAL`, `MISSING`, `INTENTIONALLY_DIFFERENT`,
  `INTENTIONALLY_UNSUPPORTED`, `UPSTREAM_DELTA`, `BLOCKED`, `UNKNOWN`) is used
  in `component_matrix.csv` and `COMPLETION_DASHBOARD.md`. The project's own
  six-value vocabulary in `docs/migration/STATUS_POLICY.md` remains the
  authoritative register; `PORT_COMPLETENESS.md` maps the two.

## Read in this order

| File | Purpose |
|---|---|
| `00_inventory.md` | factual map of the workspace, crates, submodules, toolchain, bindings |
| `00_baseline.md` | commands actually run, with results and log paths |
| `COMPLETION_DASHBOARD.md` | verified / unverified / broken / partial / missing, with priorities |
| `component_matrix.csv` | upstream component → Rust crate/symbol → status → evidence |
| `00_risks.md` | P0/P1/P2 risks and execution order |
| `legacy_dependency_register.md` | every remaining non-Rust dependency |
| `PORT_COMPLETENESS.md` | per-component completeness and the status mapping |
| `SECURITY_AND_FFI.md` | unsafe/FFI inventory and open hardening items |
| `numerics/` | formulation, invariants, gold registry, convergence, error budget |
| `compatibility/` | XML/HDF5/Touchstone and Python/MATLAB/Octave surfaces |
| `performance/` | recorded CPU/memory baseline; no accepted threshold yet |
| `gpu/` | scope decision and the upstream delta |
| `cst/` | CST import/compare template; no reference data present |
| `gui/WORKFLOW_AUDIT.md` | workbench audit and the geometry-editor scope |
| `releases/FINAL_READINESS.md` | evidence-based release recommendation |

Detailed historical evidence stays in `docs/migration/` (register, validation,
tolerances, acceptance). This audit cites it; it does not duplicate it.
