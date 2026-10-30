# Rust Migration Remediation Plan

**Status:** Proposed — requires the decisions in Section 2 before any code work.
**Date:** 2026-10-24
**Scope:** Repair the Rust migration so that it satisfies `AGENTS.md` Sections 17
and 21. This plan extends `MIGRATION_PLAN.md`; it does not replace the original
audit, baseline, or coverage records.
**Task list:** `docs/migration/REMEDIATION_TASKS.md` (IDs `RM-001` .. `RM-133`).

---

## 1. Why a remediation plan is needed

A read-only audit of both Rust trees found that the migration is not complete
and, in the numerical core, is not scientifically usable yet. Two independent
Rust implementations exist in the same repository:

| Tree | Branch / commit | Content | Verified test count |
| --- | --- | --- | --- |
| `D:/openEMS-Project` | `modernization/integration` / `a56e922` | 3 crates under `rust/`: `fparser-rs`, `csxcad-core` (811 lines), `openems-core` (basic FDTD only) | 52 + 3 + 6 = 61 |
| Worktree `mberkanbicer-potential-garbanzo` | `mberkanbicer-rust-migration-audit` / `205769d` | 13 crates: submodule ports `CSXCAD/rust`, `openEMS/rust`, `QCSXCAD`, `AppCSXCAD`, `hyp2mat/rust`, `CTB/rust`, plus Python/MATLAB bindings | fparser 52, CSXCAD 145, openEMS 117, hyp2mat 14 = 328; CTB 0 |

Commands actually run during the audit:

```text
cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs
  -> fparser 52 pass, csxcad 145 pass, openems 117 pass, hyp2mat 14 pass, ctb 0 tests
cargo test -p openems-core   -> 117 pass, exit 0
cargo metadata --no-deps     -> 13 workspace members
```

No Rust test reads `docs/migration/reference-data/`; there is no differential
or analytical comparison against the native stack. Passing tests therefore do
not constitute scientific evidence.

### 1.1 Finding register

Severity: **S1** blocks scientific correctness or makes a user-visible feature
silently wrong; **S2** blocks compatibility/completeness; **S3** process or
documentation integrity.

| ID | Sev | Finding | Evidence |
| --- | --- | --- | --- |
| F-01 | S3 | Two divergent Rust codebases with the same crate names | `rust/` vs worktree submodule crates |
| F-02 | S3 | Migration commits live on detached HEAD in all seven submodules; root workspace files are untracked | `git branch -a --contains <sha>`; `git status` in worktree |
| F-03 | S3 | `TASKS.md` marks Tasks 17-19 "Done"; code contains placeholders and no scientific validation | worktree `tasks/todo.md`, `openEMS/rust/src/processing.rs` |
| F-04 | S2 | Rust artifacts are never installed; `INSTALL_COMMAND ""` in CMake and no install step in the script | root `CMakeLists.txt`, `update_openEMS.sh:446-553` |
| F-05 | S2 | Python modules/classes are named `openems_py`, `PyOpenEMS`, `PyStructure`; native names are `openEMS`, `ContinuousStructure` | `openEMS/rust-py/src/lib.rs`, `CSXCAD/rust-py/src/lib.rs` |
| F-06 | S2 | `ctb-rs` has no binary target although the install help advertises `bin/ctb-rs` | `CTB/rust/Cargo.toml`, `update_openEMS.sh` post-install text |
| F-07 | S1 | Excitation uses the timestep index as seconds (`t = ts`) and omits `dt`, the Gaussian carrier and the native delay | `openEMS/rust/src/extensions.rs:118-147` |
| F-08 | S1 | No physics extension is ever registered by `OpenEMS::setup_fdtd`; `add_extension` has no caller outside tests | `openEMS/rust/src/openems.rs:343-416` |
| F-09 | S1 | `pml_size`, `mur_v_ph`, time-step method/factor, oversampling, thread count and cell-constant mode are stored but never read | `openEMS/rust/src/openems.rs`; grep shows only definitions/tests |
| F-10 | S1 | Non-uniform mesh is collapsed to one scalar `grid_delta` computed from the first and last line | `openEMS/rust/src/operator.rs:137-155` |
| F-11 | S1 | Material application fills a primitive's bounding box (sphere/cylinder become blocks) and ignores property/primitive priority and sub-cell averaging | `openEMS/rust/src/operator.rs:713-753` |
| F-12 | S1 | `material_grid` is allocated once per cell but indexed as three components; Ey/Ez always fall back to background | `openEMS/rust/src/operator.rs:56,342` |
| F-13 | S1 | Conductivity terms multiply by `EPS0`; native `EC_G = kappa * area / len` has no such factor | `openEMS/rust/src/operator.rs:357-359` vs `openEMS/FDTD/operator.cpp:1691` |
| F-14 | S1 | PEC/PMC boundary code zeroes the normal field component as well as the tangential ones | `openEMS/rust/src/operator.rs:441-574` |
| F-15 | S1 | Only the Var1 timestep estimate exists; native default is Var3 | `openEMS/FDTD/operator.cpp:57` |
| F-16 | S1 | End criteria never evaluates because the steady-state extension is not registered | `openEMS/rust/src/openems.rs:436-455` |
| F-17 | S1 | With no CSX input the solver fabricates a grid from `f0` and runs anyway | `openEMS/rust/src/openems.rs:359-379` |
| F-18 | S1 | The `Processing` trait has no engine/field access, so no probe or dump can sample the simulation | `openEMS/rust/src/processing.rs:17-99` |
| F-19 | S1 | `FieldProbe::process` and frequency-domain sampling are explicit placeholders | `openEMS/rust/src/processing.rs:295-350` |
| F-20 | S1 | `NF2FF` and `SAR` are dead-code shells with no transform or integration | `openEMS/rust/src/processing.rs:1157-1299` |
| F-21 | S1 | `HDF5FileWriter` writes a private `OHDF` binary, not HDF5 | `openEMS/rust/src/processing.rs:1331-1350` |
| F-22 | S1 | VTK writer emits a 1-D `DIMENSIONS n 1 1` dataset, not the native mesh/field layout | `openEMS/rust/src/processing.rs:1383-1406` |
| F-23 | S2 | Python surface is partial: no `ports`, `nf2ff`, `automesh`, `utilities`, `HDF5Dump`, `readSAR`; `add_processing` and `CreateNF2FFBox` raise | `openEMS/rust-py/src/lib.rs:330-440` |
| F-24 | S2 | MATLAB surface is a flat C ABI, not the 96 openEMS / 114 CSXCAD M-file contracts | `openEMS/rust-matlab`, `CSXCAD/rust-matlab` |
| F-25 | S2 | GUI is a prototype; central panel is a placeholder and VTK/STL/PLY/POV/X3D/PNG exports are fake (empty or fixed geometry) | `AppCSXCAD/rust/src/app.rs:166,307+`; `QCSXCAD/rust-egui/src/renderer.rs:299` |
| F-26 | S2 | hyp2mat misses polygon edge/boolean operations, PDF circles are rectangles, no `.hyp` fixture conversion test | `hyp2mat/rust/src/polygon.rs:197,202`; `pdf.rs:89` |
| F-27 | S2 | CTB has zero tests, scalar reference impedance only (native supports per-port vectors), no binary | `CTB/rust/src/lib.rs:130-330` |
| F-28 | S1 | No differential/scientific test against the captured native baselines | no `reference-data` reference in any `.rs` |
| F-29 | S2 | No Rust build/runtime job on any CI platform | repository workflows |
| F-30 | S3 | Validation/test counts in `VALIDATION.md` are stale (90 vs 117; separate "processing" crate that no longer exists) | worktree `docs/migration/VALIDATION.md:1054-1099` |

---

## 2. Decisions required before implementation

| ID | Decision | Recommended option | Blocks |
| --- | --- | --- | --- |
| D-01 | Which tree is canonical? | Worktree (`mberkanbicer-rust-migration-audit`) because it contains the submodule ports and 13-crate workspace; archive the 3-crate `rust/` duplicate on `modernization/integration` after a tagged snapshot. | Everything (M0) |
| D-02 | Engine variant scope for the first acceptance gate | Basic `Engine` + multithreaded engine; SSE/SSE-compressed and cylindrical/multigrid behind an explicit "unsupported" error until separately accepted. | RM-061, RM-062 |
| D-03 | HDF5 implementation | Keep the existing system-HDF5 FFI pattern already used by `CSXCAD/rust`; no new pure-Rust dependency unless packaging requires it. | RM-076, RM-077 |
| D-04 | GUI framework | Keep `egui` + `wgpu` (already approved in the worktree) and reach feature parity; do not restart on Qt bindings. | WS7 |
| D-05 | MATLAB strategy | Make the Rust CLI binary-compatible with the native `openEMS` executable first, so the unchanged M-file suite drives it; keep a C ABI only for CSXCAD structure access. | RM-091..RM-093 |
| D-06 | fparser optional numeric backends | Formally accept `f64`-only as documented, or implement `long double`/MPFR/GMP. Default: accept as a recorded exception. | RM-024 |
| D-07 | Numerical tolerances | Approve per-case tolerances derived from `VALIDATION.md` repeatability before any differential test is declared passing. | RM-119 |

**Stop condition:** if D-01 is not resolved, do not start WS1-WS9 work; any new
code would deepen the fork.

---

## 3. Rules of engagement

1. `AGENTS.md` is binding: preserve native behaviour and formats, do not change
   the governing equations, do not hide discrepancies, do not call a component
   complete without evidence.
2. Status vocabulary is the closed set from `AGENTS.md` Section 17:
   `Not Started`, `Analyzed`, `Implemented`, `Integrated`, `Verified`,
   `Blocked`. Only `Verified` counts as complete.
3. A task may move to `Implemented` only when the code path is reachable from a
   real entry point (CLI, Python, MATLAB, GUI, or a library API used by one of
   them). Unit-only classes do not count as integrated.
4. A task may move to `Verified` only with a recorded command, its output, and
   the reference it was compared against. "It builds" and "the test suite is
   green" are not verification of physics.
5. No new placeholder is allowed. The strings/exports below are forbidden in
   new code: `todo!()`, `unimplemented!()`, "placeholder", "not yet
   implemented", silent `_ => {}` fallbacks for user-visible options, and
   fabricated defaults that substitute for required input.
6. All Rust changes remain in the owning submodule; root pointer bumps are
   separate commits. Commits carry the `AI_POLICY.md` trailers.
7. The native C/C++ tree stays intact as the reference until the replacement is
   `Verified`.

---

## 4. Target architecture

### 4.1 Single workspace

One Cargo workspace at the repository root, members:

```text
fparser/rust            fparser-rs        (LGPL, no deps)
CSXCAD/rust             csxcad-core       (LGPL, fparser-rs)
CSXCAD/rust-py          csxcad-python     (cdylib, PyO3)
CSXCAD/rust-matlab      csxcad-matlab     (cdylib, C ABI)
openEMS/rust            openems-core      (GPL, csxcad-core + fparser-rs)
openEMS/rust-py         openems-py        (cdylib, PyO3)
openEMS/rust-matlab     openems-matlab    (cdylib, C ABI)
openEMS/rust-cli        openems-cli       (bin)
QCSXCAD/rust            qcsxcad-core      (LGPL)
QCSXCAD/rust-egui       qcsxcad-egui      (lib)
AppCSXCAD/rust          appcsxcad         (bin)
hyp2mat/rust            hyp2mat-rs        (lib + bin)
CTB/rust                ctb-rs            (lib + bin or MEX gateway; see D-05)
```

The duplicate `D:/openEMS-Project/rust/` tree is archived, not maintained in
parallel.

### 4.2 Dependency direction

`fparser-rs` -> `csxcad-core` -> `openems-core` -> {`openems-cli`,
`openems-py`, `openems-matlab`, GUI}. No downward or circular dependency.
Bindings contain no numerical logic.

### 4.3 Install layout

```text
$PREFIX/bin/openems, openems-cli, hyp2mat-rs, appcsxcad, ctb-rs (if D-05 keeps it)
$PREFIX/lib/libcsxcad_core.*, libopenems_core.*, libcsxcad_matlab.*, libopenems_matlab.*
$PREFIX/lib/python<ver>/site-packages/CSXCAD/..., openEMS/...
$PREFIX/share/openEMS/matlab/...   (M-files)
$PREFIX/share/openEMS/python/...   (pure-Python helpers, if not in the wheel)
```

Every advertised path must be produced by an install step and checked by
`RM-017`.

---

## 5. Workstreams

### WS0 — Governance and consolidation (S3)

**Current:** two trees, detached submodule commits, overstated statuses.

**Required work**
- Resolve D-01; tag the archived tree and delete the duplicate crate copies.
- Move each submodule's Rust commits onto a named branch and push before any
  root pointer bump.
- Commit the root `Cargo.toml`, `Cargo.lock`, `tasks/` if they remain part of
  the workflow, and remove generated files from the tree.
- Introduce the status/evidence policy (Section 3) and a CI check that fails on
  forbidden placeholder markers in changed Rust files (allowlist for legitimate
  cases such as `unreachable!` invariants).
- Rewrite `TASKS.md` Tasks 17-19 from "Done" to their actual state.

**Acceptance:** one canonical tree; `git submodule status` shows committed,
reachable pointers; no duplicate crates; `TASKS.md` reflects reality.

### WS1 — Build, install, packaging (S2)

**Current:** builds happen, but nothing is installed; Python wheels are not
installed; advertised binaries do not exist.

**Required work**
- Add real `INSTALL_COMMAND`/`install()` rules for every crate, or replace the
  CMake ExternalProject approach with one `cargo build --workspace` plus an
  explicit install script.
- Install wheels (`maturin build` + `pip install --no-index <wheel>` or
  `maturin develop` in a venv), rename modules/classes to the native names, and
  install M-files/CLI shims.
- Add a target for `ctb-rs` (binary or documented library/MEX only).
- Verify from a clean prefix on Linux (WSL) and Windows.

**Acceptance:** `RM-017` clean-prefix install; `python -c "import CSXCAD,
openEMS"` works; `openems --help`, `hyp2mat-rs --help`, `appcsxcad` run.

### WS2 — fparser closure (S2/S3)

**Current:** strong; optimizer equivalence is measured, not proven; optional
backends out of scope by documentation only.

**Required work:** close or formally record D-06; add cross-platform runtime
runs; add integration tests through `csxcad-core` expressions.

**Acceptance:** recorded exception or completed backends; integration tests
green on all supported platforms.

### WS3 — CSXCAD core closure (S2)

**Current:** the most mature crate (145 tests); XML/model coverage still needs
native fixture differential runs, and the Python/MATLAB surfaces are far from
the native declarations.

**Required work:** complete XML dispatch and round-trip fixtures from the native
writer; differential model tests; wire the `hdf5` feature into CI; raise Python
and MATLAB surfaces to the native class/function inventory.

**Acceptance:** native fixtures parse/serialize identically; Python/MATLAB
inventory cross-check passes; discrete-material HDF5 test runs.

### WS4 — openEMS solver correctness (S1)

This is the blocking workstream. Details in Section 6.1-6.4.

**Acceptance:** the four reference cases in `reference-data/` reproduce native
intermediate field states within approved tolerances; Mur and UPML reduce
reflection by the measured native amount; conductive and anisotropic materials
match analytic/native values.

### WS5 — Processing and file I/O (S1)

Details in Section 6.5.

**Acceptance:** native HDF5/VTK files load in Rust and Rust files load in the
unchanged Python/MATLAB readers; NF2FF and SAR match native outputs on the
reference cases.

### WS6 — Scripting interfaces (S2)

Details in Section 6.6.

**Acceptance:** unchanged native Python (31 tests + 150 CSXCAD tests) and Octave
(10 suite cases + 2 smoke tests) suites pass against the Rust backend.

### WS7 — GUI (S2)

**Current:** prototype; fake exports.

**Required work:** render every primitive; structure tree; property/material/
excitation editors; mesh line and parameter editing; real VTK/STL/PLY/POV/X3D
export from the model; PNG capture from the wgpu frame; settings and recent
files; keyboard shortcuts. Provide a manual QA checklist because there are no
automated GUI tests.

**Acceptance:** QA checklist signed; exported files open in ParaView/MeshLab and
contain the loaded geometry, not fixed placeholders.

### WS8 — hyp2mat and CTB (S2)

**Required work:** fixture corpus and conversion parity for hyp2mat; polygon
booleans/edges; QucsStudio/PDF parity. For CTB: per-port reference vectors,
complete transforms, Touchstone v1/v2, network operations, unit tests derived
from the MATLAB probes, and a delivery form that MATLAB/Octave can call.

**Acceptance:** fixture conversions byte/numerically comparable; CTB results
match the recorded MATLAB probes within tolerance; CTB has real tests.

### WS9 — Validation and CI (S1)

**Required work:** differential harness over `reference-data/`; tolerance
approval record; cross-platform CI; performance and memory baselines;
nightly reference job; full acceptance audit.

**Acceptance:** every coverage row has implementation + integration + validation
evidence; no row claims `Verified` without a recorded run.

### WS10 — Documentation and status (S3)

**Required work:** correct statuses and counts; closed status vocabulary in the
matrix; ADRs for D-01..D-07; session records that match the tree.

---

## 6. Technical specifications

### 6.1 TS-1 Excitation (`RM-037`..`RM-039`)

Replace the analytic per-step evaluation with precomputed signal arrays, exactly
as `openEMS/FDTD/excitation.cpp`:

- Voltage signal sampled at `t = n*dt`; current signal at `t = (n+0.5)*dt`.
- Length `ceil(18/(2*pi*fc)/dt)`, capped at the maximum timestep count.
- Gaussian:
  `v[n] = cos(2*pi*f0*(t - 9/(2*pi*fc))) * exp(-(2*pi*fc*t/3 - 3)^2)`;
  `v[0] = 0`; same formula at half-step for the current array.
- Sinusoidal: length `round(2/f0/dt)`; `v[n] = sin(2*pi*f0*t)`; `v[0] = 0`.
- Dirac: length 2, `[0, 1]` in both arrays.
- Step: length 2, `[1, 1]` in both arrays.
- Custom: `nTS` samples, `fparser` evaluated at `t` (voltage) and `t+dt/2`
  (current); parse errors are fatal and reported.
- `GetNyquistNum = floor(1/(2*fmax*dt))`, `UINT_MAX` when `fmax == 0`.
- Tests must capture native arrays for representative `(f0, fc, dt)` tuples and
  compare element-wise (f32) or within a stated tolerance if compiler rounding
  differs.

### 6.2 TS-2 EC coefficients and materials (`RM-047`..`RM-055`)

- Mesh: `discLines[3]`, `numLines[3]`; `GetEdgeLength(dir,pos)` and
  `GetEdgeArea(dir,pos)` from the real (possibly non-uniform) lines. Remove the
  global `grid_delta` from coefficient computation.
- Primary edges: `C = eps_abs * area/len`, `G = kappa * area/len`.
- Dual edges: `L = mue_abs * area_dual/len_dual`,
  `R = sigma * area_dual/len_dual`.
- No `EPS0` factor on `G` or `R`.
- Effective material per edge from `Calc_EffMatPos`: property/primitive priority
  order, sub-cell averaging, anisotropic `[eps, kappa, mue, sigma]` vectors.
- Storage is `[3][nx][ny][nz]` (or an `ArrayNIJK`) everywhere; no 1x/3x index
  mismatch.
- Metal/PEC: zero `vv`/`vi` on the tangential edges covered by the metal
  primitive; apply caps where the native code does.
- Every coefficient write is direction-specific; tests must assert that Ex, Ey,
  Ez see different materials in an anisotropic fixture.

### 6.3 TS-3 Extension system (`RM-040`..`RM-046`, `RM-056`..`RM-060`)

- Add `OperatorExtension` with the native hook set, mirroring
  `Common/operator_base.h`: pre/post voltage and current updates, `Apply2*`,
  priority get/set.
- `OpenEMS::setup_fdtd` constructs extension pairs from the parsed structure in
  native order: excitation, Mur or UPML (per face), TFSF, dispersive materials,
  conducting sheets, lumped RLC, cylinder, steady state.
- Both operator and engine lists are kept sorted by native priority constants;
  a test asserts the resulting order.
- PML/UPML: compute the native sigma/kappa/alpha profiles and `vv/vvfo/vvfn`,
  `ii/iifo/iifn` coefficients in an operator extension; the engine extension
  only applies them. `pml_size` and the XML boundary properties feed this path.
- Mur: per-face coefficient uses the local cell delta and the configured phase
  velocity; no hard-coded `1e-3`.
- Steady-state extension provides the end-criterion value to `run_fdtd`.

### 6.4 TS-4 Mesh and timestep (`RM-047`..`RM-049`, `RM-063`)

- Implement `CalcTimestep_Var1` and `CalcTimestep_Var3`; default Var3; honor
  `time_step_method`, `time_step_factor`, and an explicit fixed timestep.
- Keep the native "adjust dt to a periodic signal" behaviour when a sinusoidal
  excitation is used.
- `max_time`, `over_sampling`, `abort`, and thread count must have observable
  effects or return an explicit error when unsupported.

### 6.5 TS-5 Processing and file formats (`RM-066`..`RM-082`)

- Introduce `EngineInterface` (field getters, mesh, dt, timestep, number of
  lines) and pass it to `Processing::process(interface, num_ts)`.
- Time-domain probe, running DFT (with the native frequency list and
  oversampling), integral/voltage/current, TD/FD field dumps, mode match, SAR,
  NF2FF.
- HDF5: reproduce the native dataset names, attributes, compound/split-complex
  layouts, mesh attributes, units and legacy axis order; read native files and
  write files the unchanged Python `HDF5Dump` and MATLAB readers accept.
- VTK: real `STRUCTURED_POINTS` grid with actual dimensions, origin, spacing and
  vector fields.
- Dump scheduling, file naming, `flush`/close semantics as in the native
  processing array.
- NF2FF and SAR must use the native algorithms (port `openEMS/nf2ff/` and the
  SAR integration), not a new formulation.

### 6.6 TS-6 Interfaces (`RM-083`..`RM-096`)

- **CLI first:** implement the native `openEMS` command-line contract
  (`--SetupFileName`, `--CSXGeoFile`, `--FDump`, engine selection, verbosity,
  exit codes, log files) so the unchanged M-file/Octave suite can drive it.
- **Python:** package `CSXCAD` and `openEMS`; native class names
  (`ContinuousStructure`, `CSProperties`, `CSPropMaterial`, `openEMS`,
  `CSXRectGrid`, ...); `ports.py`, `nf2ff.py`, `automesh.py`, `utilities.py`;
  `add_processing` and NF2FF creation must work, not raise.
- **MATLAB:** install the native M-files and make them resolve to the Rust
  executable/library; keep the C ABI only where direct structure access is
  needed. Run the native `TESTSUITE` unchanged.
- Errors, default values, ownership/lifetime and array orientation must match
  the audited contracts.

### 6.7 TS-7 GUI (`RM-097`..`RM-106`)

- Build geometry from the full `Structure` model (all primitive types,
  transforms, parameters), not a placeholder cube.
- Editors for primitives, properties, materials, excitations, probes/dumps,
  mesh lines and parameters; tree view; undo/redo; shortcuts.
- Exports must serialize the actual model: VTK polydata, STL, PLY, POV-Ray,
  X3D; PNG via wgpu texture readback.
- A written manual QA checklist covers load/edit/save, each export, and view
  controls.

---

## 7. Milestones and gates

| Milestone | Content | Gate |
| --- | --- | --- |
| **M0** | D-01 decided; submodule branches pushed; duplicate archived; statuses corrected | `git submodule status` clean and reachable; one workspace |
| **M1** | WS1 complete: installable prefix, importable Python, runnable binaries | `RM-017` clean-prefix test passes |
| **M2** | WS4 complete: solver P0 fixes + analytic differential | `RM-065` passes on all four reference cases |
| **M3** | WS5 complete: real probes/dumps/NF2FF/SAR + file compatibility | `RM-081` file-level differential passes |
| **M4** | WS6 complete: native Python/Octave suites pass unchanged | `RM-095`, `RM-096` |
| **M5** | WS7/WS8 complete: GUI parity, hyp2mat/CTB parity | QA sign-off; fixture parity |
| **M6** | WS9/WS10 complete: full acceptance | `AGENTS.md` Section 21 checklist signed |

No milestone may be declared while any of its tasks is `Implemented` but not
`Verified`.

---

## 8. Verification strategy

1. **Differential harness (`RM-117`):** Rust binary/API reads the captured
   inputs and emits intermediate and final arrays; a comparator reads the native
   references under `docs/migration/reference-data/`.
2. **Cases:** 1-D conducting sheet (analytic), 3-D coax (analytic port
   impedance), MSL notch smoke (field/port traces), analytic dipole
   (FieldProbes), plus one non-uniform-mesh case and one anisotropic-material
   case that the current suite lacks.
3. **Comparisons:** exact for integer/structural data; per-case absolute,
   relative and norm tolerances for fields; complex values compared by
   magnitude and phase; near-zero handled explicitly.
4. **Tolerances (`RM-119`):** derived from the recorded native repeatability
   (bitwise repeat was observed for saved port arrays; field arrays repeat
   exactly within a platform). Cross-platform/parallel order differences must be
   justified, never used to hide a defect.
5. **No test may be adjusted to pass.** If Rust and native disagree, the
   discrepancy is investigated and recorded.

---

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Canonical tree not agreed | Two forks diverge further | D-01 is a hard gate; archive the loser immediately |
| Solver rewrite grows unbounded | Never reaches acceptance | Fix P0 list first, gate on differential cases; defer engine variants per D-02 |
| HDF5 FFI packaging breaks on some platforms | I/O unusable | Keep the existing system-HDF5 path, add CI coverage, document the dependency |
| Python/MATLAB surfaces are much larger than estimated | Interfaces slip | CLI-first strategy for MATLAB; generate the Python surface from the audited inventory |
| GUI parity is open-ended | Blocks acceptance | Approve a bounded workflow list (load/edit/save/export/view) and treat it as the contract |
| Submodule ownership/licensing mistakes | Unlandable changes | Branch + push per submodule, pointer bump only after push, AI_POLICY trailers |
| Existing defects in native code surface during differential | Confusion about which side is wrong | Record native defects separately (as already required by `AGENTS.md`); do not "fix" them silently in Rust |

---

## 10. Out of scope / to be recorded as exceptions

Any item not implemented must be recorded in the exception register
(`RM-126`) with justification, user impact, and the native compatibility path.
Candidates:

- fparser optional numeric backends (D-06).
- SSE/SSE-compressed and cylindrical/multigrid engines (D-02), if deferred.
- Interactive GUI behaviours that cannot be automated (manual QA only).
- Native defects confirmed during differential work (documented, not silently
  reproduced).

---

## 11. Traceability matrix

| Finding | Tasks |
| --- | --- |
| F-01, F-02 | RM-001..RM-005 |
| F-03, F-30 | RM-006, RM-128..RM-133 |
| F-04..F-06 | RM-009..RM-022 |
| F-07 | RM-037..RM-039 |
| F-08, F-09 | RM-040..RM-046, RM-056..RM-064 |
| F-10, F-15 | RM-047..RM-049 |
| F-11, F-12, F-13 | RM-050..RM-055 |
| F-14 | RM-045, RM-046 |
| F-16, F-17 | RM-060, RM-064 |
| F-18..F-22 | RM-066..RM-082 |
| F-23, F-24 | RM-083..RM-096 |
| F-25 | RM-097..RM-106 |
| F-26, F-27 | RM-107..RM-116 |
| F-28, F-29 | RM-117..RM-127 |

---

## 12. Progress log

Append one entry per session: date, tasks moved, commands run, evidence paths,
blockers, next task. Do not rewrite history.

| Date | Task(s) | Status change | Evidence |
| --- | --- | --- | --- |
| 2026-10-24 | Audit | Plan created | This document; `REMEDIATION_TASKS.md` |
| 2026-10-24 | RM-001 | Verified | `docs/adr/0001-canonical-rust-tree.md` |
| 2026-10-24 | RM-037..RM-039, RM-050, RM-054 | Implemented | `openEMS/rust/src/{excitation,extensions,operator}.rs`; `cargo test -p openems-core` -> 124 passed; details in `REMEDIATION_TASKS.md` progress evidence |
| 2026-10-24 | RM-045, RM-046 | Implemented | Tangential-only PEC/PMC boundary application with normal-component tests; `cargo test -p openems-core` -> 126 passed |
| 2026-10-24 | RM-041, RM-044, RM-047, RM-048, RM-051, RM-055, RM-064 | Implemented | Solver wiring slice: CSX excitation -> Yee edges, native Mur coefficients/three-phase update, non-uniform mesh geometry, priority/containment materials, PEC edges, required CSX input. `cargo test -p openems-core` -> 134 passed (345 across the numerical crates) |
| 2026-10-24 | Bug fix (RM-037/038/041) | Implemented | Timestep ordering: `calc_timestep` now precedes `calc_ec_operator`; the previous order left `vi`/`iv` zero and blocked wave propagation. Neighbour-cell propagation is now asserted. 135 openEMS-core tests / 346 numerical-core tests pass |
| 2026-10-24 | RM-066, RM-067 | Implemented | Engine interface and time-domain probe wiring; `run_fdtd` now drives `process_fields` with live fields. 137 openEMS-core tests pass |
| 2026-10-24 | RM-068 | Implemented | Running DFT accumulation in `FieldProbe` with on-bin/off-bin verification. 138 openEMS-core tests pass |
| 2026-10-24 | RM-071, RM-078 | Implemented | Real structured-grid VTK writer and time-domain field dump processing. 139 openEMS-core tests pass |
| 2026-10-24 | RM-042, RM-043 | Implemented | UPML enabled and validated: 6 GHz pulse in a 41x21x21 mm box with 8-cell PML ends at 1.4e-6 of its peak (-117 dB), versus 1.3e-2 for PEC. Native coefficient-level comparison still open |
| 2026-10-24 | RM-049 | Implemented | CFL Var1/Var3 selection with native `AdrOp` boundary reflection; both agree with the uniform-mesh analytic values (`delta/2c` and `delta/(sqrt(3)c)`) to 1e-6 |
| 2026-10-24 | RM-052 | Implemented | Native quarter-cell material averaging (area-weighted eps/kappa, harmonic mue/sigma) with an analytic half-space test (2.5 at the interface) |
| 2026-10-24 | RM-072 | Implemented | Running DFT frequency-domain dumps with native Nyquist/oversampling intervals, VTK magnitude/phase/phase-snapshot files and native HDF5 `f0..fn` real/imag output |
| 2026-10-24 | RM-076, RM-077 | Implemented | Real system-HDF5 writer/reader (`hdf5` feature, `build.rs`) with the native `/Mesh` + `/FieldData/{TD,FD}` layout, `d_order`, `time` and `frequency` attributes; reads the recorded C++ dump `Et_ref.h5` and round-trips its layout. 158 openEMS-core tests pass with `--features hdf5` |
| 2026-10-24 | RM-053 | Implemented | CSXCAD infers anisotropy from per-direction property vectors (`Epsilon="2,4,6"`) and the EC coefficients follow each edge direction (vi_x:vi_y:vi_z = 1/2:1/4:1/6) |
| 2026-10-24 | RM-065 (partial) | Not Started | New analytic integration suite: vacuum pulse speed 2.9404e8 m/s (1.9% vs c) and dielectric speed c/2 (1.0%); full case set still open |
