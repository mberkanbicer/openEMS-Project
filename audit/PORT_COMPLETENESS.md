# Port completeness

## 1. Status vocabulary mapping

The project register (`docs/migration/REMEDIATION_TASKS.md`) uses
`Not Started / Analyzed / Implemented / Integrated / Verified / Blocked`. This
audit uses the protocol taxonomy. Mapping used in `component_matrix.csv`:

| Audit status | Project status | Meaning |
|---|---|---|
| `VERIFIED_COMPLETE` | `Verified` with an executed comparison | implementation + evidence |
| `IMPLEMENTED_UNVERIFIED` | `Implemented`/`Integrated` | code exists, evidence insufficient |
| `IMPLEMENTED_BROKEN` | any status + a reproducible defect | defect confirmed |
| `PARTIAL` | `Implemented` with an unfinished segment | end-to-end incomplete |
| `MISSING` | `Not Started` | no implementation |
| `INTENTIONALLY_DIFFERENT` | accepted exception/ADR | documented divergence |
| `INTENTIONALLY_UNSUPPORTED` | accepted exception/ADR | out of scope |
| `BLOCKED` | `Blocked` | external dependency |
| `UNKNOWN` | — | not investigated |

The register now reports **172 `Verified`, 0 open rows** after RM-167..RM-172.
This audit adds subsystem-level findings the row status did not capture (two P0
silent option drops, now guarded).

## 2. Component summary

| Upstream component | Rust crates | State |
|---|---|---|
| `openEMS` solver | `openems-core`, `openems-cli`, `nf2ff-cli`, `sar-cli`, `openems-py`, `openems-matlab` | core operator/engine/extensions/probes/NF2FF/SAR implemented; 51-case differential harness + analytic wave speed; GPU compute excluded (ADR 0002); multi-grid and cell-constant material now **fail loudly** (E-007/E-008) |
| `CSXCAD` | `csxcad-core`, `csxcad-python`, `csxcad-matlab` | model/grid/materials/transforms/parameters/XML/HDF5 implemented; 11 native XML fixtures; 216 crate tests |
| `QCSXCAD` | `qcsxcad-core`, `qcsxcad-egui` | document/project/tessellation/export + egui/wgpu editor |
| `AppCSXCAD` | `appcsxcad` | standalone desktop app; geometry editor scope (no solver run, like native) |
| `fparser` | `fparser-rs` | expression parser; f64 only (E-001) |
| `hyp2mat` | `hyp2mat-rs` | PCB/HyperLynx importer; 9/9 model dumps byte-identical; FreeBSD excluded (E-004) |
| `CTB` | `ctb-rs` + M-files | network conversions/Touchstone; differential + Octave exercise |

## 3. What is complete (do not re-port)

- FDTD update coefficients, CFL Var1/Var3, engine stepping (f32 fields).
- UPML, Mur, TFSF, excitations, dispersive ADE, conducting sheet, lumped RLC,
  steady state, cylindrical r=0/seam.
- Probes/DFT, HDF5/VTK output, NF2FF, SAR.
- CSXCAD geometry/materials/parameters/XML/transforms and HDF5 geometry I/O.
- fparser f64, hyp2mat, CTB.
- Python and MATLAB/Octave surfaces, CLI names and the install layout.
- GUI editor workflow and theme layer.

## 4. Proven gaps and their disposition

| Gap | Disposition |
|---|---|
| `CellConstantMaterial` silently ignored | **Fixed**: setup rejects it, E-008, test |
| `MultiGrid` silently ignored; RM-061 had no evidence | **Fixed**: setup rejects stored radii, E-007, tests, register corrected |
| Python façade drifted from carried upstream tests | **Fixed**: `dc_free`, engine diagnostics, `Write2XML` completeness, `GetPolyDataModel` arrays/live transform |
| GPU compute | `INTENTIONALLY_UNSUPPORTED` (ADR 0002); GPU tests are reported `SKIPPED`, never passed |
| CST comparison | `BLOCKED`: no licence/data |
| Mesh/time convergence | `PARTIAL`: analytic wave speed only; no refinement table |
| Performance threshold | `PARTIAL`: refreshed baseline; proposed gate passes, not yet accepted |
| Platform matrix | `BLOCKED`: hosted Actions unavailable; last run predates HEAD |

| Parser hardening | no fuzz corpus; fparser has no nesting-depth limit (SEC-001) |

## 5. Readiness statement

The default CPU solver path is evidence-backed against the pinned native build
and analytic wave speed. The port is **not** a complete equivalent of every
upstream option (multi-grid, cell-constant materials, GPU), and those omissions
are now explicit. CST and convergence evidence do not exist. See
`releases/FINAL_READINESS.md`.
