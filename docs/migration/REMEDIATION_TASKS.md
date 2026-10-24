# Rust Migration Remediation Task List

Companion to `docs/migration/REMEDIATION_PLAN.md`.
Created 2026-10-24. Supersedes the "Done" claims for Tasks 17-19 in
`docs/migration/TASKS.md` until the acceptance evidence below exists.

## Status legend

| Status | Meaning |
| --- | --- |
| `Not Started` | No work begun |
| `Analyzed` | Original behaviour mapped, implementation not written |
| `Implemented` | Code exists and is reachable from a real entry point |
| `Integrated` | Component is wired into CLI/Python/MATLAB/GUI or a library consumer |
| `Verified` | Recorded command + output + reference comparison |
| `Blocked` | Cannot proceed; reason recorded |

Only `Verified` counts as complete (`AGENTS.md` Section 17). Unit-only classes
are `Implemented`, never `Integrated`. "It builds" is not verification.

## Rules

1. Do not move a task forward without evidence in the row's `Evidence` column.
2. Do not close a task while a forbidden placeholder remains on its path
   (`todo!()`, `unimplemented!()`, "placeholder", "not yet implemented", silent
   option drops).
3. Every submodule change is committed in the owning submodule first; a root
   pointer bump is a separate task/commit.
4. Tolerances are approved once (`RM-119`) and then reused; never relaxed to
   make a test pass.
5. If a task reveals a native defect, record it in `AUDIT_FINDINGS.md` and the
   exception register (`RM-126`); do not silently change Rust to match a bug or
   silently "fix" the native side.

## Summary

| Workstream | Tasks | P0 | P1 | P2/P3 |
| --- | --- | --- | --- | --- |
| WS0 Governance | 001-008 | 6 | 2 | 0 |
| WS1 Build/install | 009-022 | 7 | 5 | 2 |
| WS2 fparser | 023-027 | 0 | 1 | 4 |
| WS3 CSXCAD | 028-036 | 0 | 5 | 4 |
| WS4 Solver | 037-065 | 20 | 9 | 0 |
| WS5 Processing | 066-082 | 12 | 4 | 1 |
| WS6 Interfaces | 083-096 | 11 | 3 | 0 |
| WS7 GUI | 097-106 | 0 | 8 | 2 |
| WS8 hyp2mat/CTB | 107-116 | 0 | 9 | 1 |
| WS9 Validation | 117-127 | 6 | 2 | 3 |
| WS10 Documentation | 128-133 | 4 | 1 | 1 |
| **Total** | **133** | **66** | **49** | **18** |

**Critical path:** RM-001 -> RM-003 -> RM-004 -> RM-009 -> RM-010 -> RM-012 ->
RM-017 -> RM-040 -> RM-041 -> RM-042 -> RM-043 -> RM-047 -> RM-048 -> RM-050 ->
RM-051 -> RM-052 -> RM-054 -> RM-055 -> RM-065 -> RM-066 -> RM-076 -> RM-081 ->
RM-083 -> RM-091 -> RM-095 -> RM-096 -> RM-117 -> RM-118 -> RM-119 -> RM-125 ->
RM-127.

## Current status snapshot (2026-10-24)

| Status | Count | Tasks |
| --- | --- | --- |
| `Verified` | 18 | RM-001, RM-002, RM-003, RM-004, RM-005, RM-009, RM-011, RM-012, RM-014, RM-016, RM-017, RM-126, RM-128, RM-129, RM-130, RM-131, RM-132, RM-133 |
| `Implemented` | 40 | RM-037, RM-038, RM-039, RM-041, RM-042, RM-043, RM-044, RM-045, RM-046, RM-047, RM-048, RM-049, RM-050, RM-051, RM-052, RM-053, RM-054, RM-055, RM-064, RM-066, RM-067, RM-068, RM-069, RM-070, RM-071, RM-072, RM-076, RM-077, RM-078, RM-079, RM-006, RM-007, RM-008, RM-010, RM-018, RM-019, RM-020, RM-021, RM-022 |
| `Blocked` | 2 | RM-125, RM-127 |
| `Not Started` | 73 | all remaining tasks |

Estimates: S <= 1 day, M 2-5 days, L 1-2 weeks, XL > 2 weeks. Indicative only.

---






## Remaining backlog (73 tasks) and execution order

The tasks below are the `Not Started` rows of this document, grouped by the order they will be executed. Wave A is complete and pushed; the remaining waves are ordered by dependency and by what can be verified in this workspace.

### Wave B - core solver physics and processing

| ID | Pri | Task | Depends |
| --- | --- | --- | --- |
| RM-040 | P0 | Introduce `OperatorExtension` trait and priority handling | RM-004 |
| RM-056 | P1 | Wire Debye/Lorentz operator+engine extensions | RM-041 |
| RM-057 | P1 | Wire conducting-sheet extension | RM-041 |
| RM-058 | P1 | Wire lumped RLC extension | RM-041 |
| RM-059 | P1 | Wire TFSF extension | RM-041 |
| RM-061 | P1 | Cylinder/multigrid: implement or fail loudly (D-02) | RM-047 |
| RM-062 | P1 | Engine variants: multithread first; SSE decision (D-02) | RM-049 |
| RM-063 | P1 | Wire `over_sampling`, `max_time`, thread count, abort | RM-041 |
| RM-065 | P0 | Analytic differential suite: 1-D sheet, 3-D coax, MSL, dipole + non-uniform + anisotropic | RM-047..RM-055,RM-043 |
| RM-073 | P0 | Implement SAR with 1 g/10 g averaging | RM-066 |
| RM-074 | P0 | Port native NF2FF transform | RM-066 |
| RM-075 | P1 | Implement `ProcessModeMatch` | RM-066 |
| RM-081 | P0 | File-level differential tests and fixtures | RM-076..RM-079 |
| RM-082 | P2 | Document file formats and compatibility guarantees | RM-081 |

### Wave C - CLI and scripting interfaces

| ID | Pri | Task | Depends |
| --- | --- | --- | --- |
| RM-013 | P0 | Rename modules/classes to native names (`CSXCAD`, `openEMS`, `ContinuousStructure`, `openEMS`) | RM-012 |
| RM-080 | P1 | Implement Python `HDF5Dump`, `readSAR`, NF2FF readers | RM-076 |
| RM-083 | P0 | Make Rust CLI accept the native `openEMS` invocation contract | RM-065 |
| RM-084 | P0 | Match CLI options, exit codes, log files, verbosity | RM-083 |
| RM-085 | P0 | Build native Python package layout | RM-013 |
| RM-086 | P0 | Match Controller method surface, defaults, errors | RM-085 |
| RM-087 | P0 | Implement Python port classes | RM-085 |
| RM-088 | P0 | Implement Python NF2FF module | RM-074,RM-085 |
| RM-089 | P1 | Implement Python automesh and utilities | RM-085 |
| RM-090 | P0 | Raise CSXCAD Python classes to native surface | RM-031 |
| RM-091 | P0 | Make native MATLAB/Octave M-file suite work through CLI | RM-083 |
| RM-092 | P0 | Match MATLAB `calcPort`, `CalcNF2FF`, post-processing | RM-091,RM-074 |
| RM-093 | P1 | Implement CSXCAD MATLAB M-file surface | RM-032 |
| RM-094 | P1 | Match error identifiers, ownership, array orientation | RM-090,RM-093 |
| RM-095 | P0 | Run native Python suite (31 tests + 150 CSXCAD) unchanged | RM-085..RM-090 |
| RM-096 | P0 | Run native Octave suite and MSL smoke tests unchanged | RM-091..RM-093 |

### Wave D - GUI (QCSXCAD / AppCSXCAD)

| ID | Pri | Task | Depends |
| --- | --- | --- | --- |
| RM-015 | P1 | Fix `qcsxcad-egui`/`appcsxcad` target names and install behavior | RM-009 |
| RM-097 | P1 | Render every primitive type, transform and parameter | RM-006 |
| RM-098 | P1 | Structure tree with properties and primitives | RM-097 |
| RM-099 | P1 | Property/material/excitation editor | RM-097 |
| RM-100 | P1 | Primitive add/delete/modify operations | RM-099 |
| RM-101 | P1 | Mesh line and parameter editing | RM-099 |
| RM-102 | P2 | Undo/redo and keyboard shortcuts | RM-100 |
| RM-103 | P1 | File I/O, settings, CLI arguments parity | RM-098 |
| RM-104 | P1 | Real VTK/STL/PLY/POV/X3D exports from the model | RM-100 |
| RM-105 | P2 | PNG capture from the wgpu frame | RM-097 |
| RM-106 | P1 | Manual GUI QA checklist and sign-off | RM-097..RM-105 |

### Wave E - hyp2mat and CTB

| ID | Pri | Task | Depends |
| --- | --- | --- | --- |
| RM-107 | P1 | Build a `.hyp` fixture corpus from native examples/docs | RM-004 |
| RM-108 | P1 | Implement polygon edge/boolean operations | RM-107 |
| RM-109 | P1 | Match CSXCAD XML output | RM-108 |
| RM-110 | P2 | Match QucsStudio and PDF output | RM-108 |
| RM-111 | P1 | Match hyp2mat CLI options/behavior | RM-109 |
| RM-112 | P1 | CTB per-port reference impedance vectors | RM-004 |
| RM-113 | P1 | Complete CTB transform set and dimensions | RM-112 |
| RM-114 | P1 | Touchstone v1/v2 read/write parity | RM-112 |
| RM-115 | P1 | CTB network operations parity | RM-113 |
| RM-116 | P1 | CTB delivery form for MATLAB/Octave | RM-112 |

### Wave F - CSXCAD depth, validation and CI

| ID | Pri | Task | Depends |
| --- | --- | --- | --- |
| RM-023 | P2 | Close optimizer-rule differential coverage or record a bounded exception | RM-006 |
| RM-024 | P2 | Decide and implement/record optional numeric backends (D-06) | RM-006 |
| RM-025 | P2 | Decide C++ API/FFI compatibility surface | RM-006 |
| RM-026 | P2 | Run fparser differential suite on macOS and FreeBSD | RM-023 |
| RM-027 | P1 | Add integration tests through CSXCAD expression evaluation | RM-006 |
| RM-028 | P1 | Complete XML dispatch and round-trip fixtures generated by native CSXCAD | RM-004 |
| RM-029 | P1 | Differential model harness against native CSXCAD | RM-028 |
| RM-030 | P2 | Enable and validate `hdf5` feature in CI | RM-009 |
| RM-031 | P1 | Raise CSXCAD Python surface to native class inventory | RM-013 |
| RM-032 | P1 | Raise CSXCAD MATLAB surface to native M-file inventory | RM-016 |
| RM-033 | P1 | Error/ownership/lifetime contract tests | RM-028 |
| RM-034 | P2 | Transform/parameter edge-case parity | RM-028 |
| RM-035 | P2 | Extend STL/PLY/XML fixture corpus | RM-028 |
| RM-036 | P3 | CSXCAD performance baseline | RM-028 |
| RM-117 | P0 | Build differential harness over `reference-data/` | RM-065 |
| RM-118 | P0 | Execute all reference cases through the harness | RM-117,RM-066 |
| RM-119 | P0 | Approve and record tolerances | RM-118 |
| RM-120 | P1 | Cross-platform runtime CI (Linux/Windows/macOS/FreeBSD) | RM-017,RM-117 |
| RM-121 | P2 | Performance baseline vs native | RM-065 |
| RM-122 | P2 | Memory baseline vs native | RM-065 |
| RM-123 | P1 | Regression CI for unit + integration suites | RM-117 |
| RM-124 | P2 | Nightly reference run | RM-123 |

### Next queue (execution order)

1. RM-060 - steady-state extension and end criteria
2. RM-040 - `OperatorExtension` trait and priority dispatch
3. RM-057 / RM-058 - conducting-sheet and lumped-RLC extensions
4. RM-059 - TFSF extension
5. RM-056 - Debye/Lorentz dispersive materials
6. RM-073 / RM-074 / RM-075 - SAR, NF2FF and mode matching
7. RM-081 / RM-117..RM-119 - differential harness and tolerances
8. RM-083 / RM-084 - native CLI invocation contract
9. RM-063 - remaining option wiring (`over_sampling`, thread count, abort)

Wave C additionally needs a Python interpreter compatible with the PyO3 version in use; the current PyO3 0.30 supports CPython 3.14.

## WS0 - Governance and consolidation

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-001 | P0 | Decide canonical Rust tree (D-01); record in ADR | - | S | ADR with decision, archived commit/tag | Verified |
| RM-002 | P0 | Archive the losing 3-crate implementation; delete duplicate crate copies | RM-001 | S | No duplicated `fparser-rs`/`csxcad-core`/`openems-core` sources | Verified |
| RM-003 | P0 | Move seven submodule Rust commits onto named branches and push | RM-001 | M | `git branch -r --contains <sha>` lists the branch for each submodule | Verified |
| RM-004 | P0 | Bump root submodule pointers in a separate commit | RM-003 | S | Root commit message; `git submodule status` shows committed SHAs | Verified |
| RM-005 | P0 | Commit root `Cargo.toml`, `Cargo.lock`, workflow files; remove generated files | RM-001 | S | `git status` clean except intentional build output | Verified |
| RM-006 | P0 | Publish status/evidence policy and closed status vocabulary | - | S | Policy section in plan/status docs; team acknowledgement | Implemented |
| RM-007 | P1 | Add CI gate for forbidden placeholders in changed Rust files | RM-006 | S | CI job fails on seeded placeholder, passes on allowlisted `unreachable!` | Implemented |
| RM-008 | P1 | Maintain remediation register and progress log | RM-006 | S | Log entry per session in plan Section 12 | Implemented |
## WS1 - Build, install, packaging

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-009 | P0 | Replace per-crate ExternalProject builds with one workspace build + install rules | RM-001 | L | `cmake --build` + `cmake --install` produce the layout in plan 4.3 | Verified |
| RM-010 | P0 | Add real install steps to `update_openEMS.sh` (`--with-rust`) | RM-009 | M | Clean prefix contains every advertised file | Implemented |
| RM-011 | P1 | Extend `install_deps.sh --with-rust` to check cargo/maturin/toolchain | RM-010 | S | Missing tool produces actionable error | Verified |
| RM-012 | P0 | Build and install Python wheels into prefix or venv | RM-009 | M | `pip show` + import from the installed prefix | Verified |
| RM-013 | P0 | Rename modules/classes to native names (`CSXCAD`, `openEMS`, `ContinuousStructure`, `openEMS`) | RM-012 | M | `python -c "from CSXCAD import ContinuousStructure; from openEMS import openEMS"` | Not Started |
| RM-014 | P0 | Add `ctb-rs` binary target or record lib/MEX-only delivery | RM-001 | S | Target exists or exception recorded; install help matches reality | Verified |
| RM-015 | P1 | Fix `qcsxcad-egui`/`appcsxcad` target names and install behavior | RM-009 | S | Advertised binaries exist and launch | Not Started |
| RM-016 | P0 | Install MATLAB M-files and shared libraries under the prefix | RM-009 | M | Native M-file paths resolve to installed files | Verified |
| RM-017 | P0 | Clean-prefix install verification on Linux (WSL) and Windows | RM-010,012,016 | M | Recorded transcript of configure/build/install/run | Verified |
| RM-018 | P1 | Add Linux Rust build+install CI job | RM-017 | M | Green workflow | Implemented |
| RM-019 | P1 | Add Windows Rust build+install CI job | RM-017 | M | Green workflow | Implemented |
| RM-020 | P2 | Add macOS/FreeBSD build job (minimum `cargo check`) | RM-017 | M | Green/known-limitation record | Implemented |
| RM-021 | P1 | Remove the dual build path (CMake vs script) or document one entry point | RM-009 | S | Single documented command produces identical layout | Implemented |
| RM-022 | P2 | Update installation/build documentation | RM-017 | S | Docs match the verified layout | Implemented |
## WS2 - fparser closure

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-023 | P2 | Close optimizer-rule differential coverage or record a bounded exception | RM-006 | L | Measured statement with case counts and residual risk | Not Started |
| RM-024 | P2 | Decide and implement/record optional numeric backends (D-06) | RM-006 | L | ADR + tests or exception register entry | Not Started |
| RM-025 | P2 | Decide C++ API/FFI compatibility surface | RM-006 | S | ADR; bindings plan | Not Started |
| RM-026 | P2 | Run fparser differential suite on macOS and FreeBSD | RM-023 | M | Platform logs | Not Started |
| RM-027 | P1 | Add integration tests through CSXCAD expression evaluation | RM-006 | S | Tests in `csxcad-core` cover parameter/expression paths | Not Started |
## WS3 - CSXCAD closure

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-028 | P1 | Complete XML dispatch and round-trip fixtures generated by native CSXCAD | RM-004 | L | Fixture corpus + parse/serialize/parse equality | Not Started |
| RM-029 | P1 | Differential model harness against native CSXCAD | RM-028 | L | Recorded accepted/containment/bounds comparisons | Not Started |
| RM-030 | P2 | Enable and validate `hdf5` feature in CI | RM-009 | M | Discrete-material HDF5 test runs on CI | Not Started |
| RM-031 | P1 | Raise CSXCAD Python surface to native class inventory | RM-013 | L | Cross-check against 33 Cython classes | Not Started |
| RM-032 | P1 | Raise CSXCAD MATLAB surface to native M-file inventory | RM-016 | L | Cross-check against 114 M-files | Not Started |
| RM-033 | P1 | Error/ownership/lifetime contract tests | RM-028 | M | Tests for invalid handles, wrapper cache, copy semantics | Not Started |
| RM-034 | P2 | Transform/parameter edge-case parity | RM-028 | M | Differential cases recorded | Not Started |
| RM-035 | P2 | Extend STL/PLY/XML fixture corpus | RM-028 | M | VTK-verified point/face ordering | Not Started |
| RM-036 | P3 | CSXCAD performance baseline | RM-028 | M | XML load/serialize benchmark recorded | Not Started |
## WS4 - openEMS solver correctness

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-037 | P0 | Implement native excitation arrays (Gaussian/Sinus/Dirac/Step) | RM-004 | L | Element-wise comparison with native arrays | Implemented |
| RM-038 | P0 | Add current half-step signal, Nyquist count, max excitation timestep | RM-037 | M | Native array comparison for both signals | Implemented |
| RM-039 | P1 | Implement custom excitation through fparser with parse-error reporting | RM-037 | S | Native comparison for two expressions | Implemented |
| RM-040 | P0 | Introduce `OperatorExtension` trait and priority handling | RM-004 | L | Unit tests for ordering and hook dispatch | Not Started |
| RM-041 | P0 | Register extension pairs from `setup_fdtd` in native order | RM-040 | L | Integration test asserts the registered set/order for a fixture | Implemented |
| RM-042 | P0 | Implement UPML operator coefficients (vv/vvfo/vvfn, ii/iifo/iifn) | RM-040 | L | Coefficient comparison with native for a small box | Implemented |
| RM-043 | P0 | Wire UPML engine extension and measure reflection | RM-042,RM-041 | M | Reflection below approved bound; native comparison | Implemented |
| RM-044 | P0 | Fix Mur per-face delta and phase velocity | RM-041 | M | No hard-coded 1e-3; non-uniform mesh test | Implemented |
| RM-045 | P0 | Make PEC boundary tangential-only | RM-041 | S | Normal component preserved; test | Implemented |
| RM-046 | P0 | Make PMC boundary tangential-only | RM-041 | S | Normal component preserved; test | Implemented |
| RM-047 | P0 | Replace scalar `grid_delta` with `discLines[3]`/`numLines[3]` | RM-004 | L | Non-uniform mesh test with graded lines | Implemented |
| RM-048 | P0 | Implement `GetEdgeLength`/`GetEdgeArea` for non-uniform/dual mesh | RM-047 | M | Analytic checks on a graded grid | Implemented |
| RM-049 | P0 | Implement CFL Var1 and Var3, method selection, time-step factor | RM-047 | M | Native dt comparison on three meshes | Implemented |
| RM-050 | P0 | Fix material storage to a 3-component layout | RM-047 | S | Ey/Ez see material; anisotropic test | Implemented |
| RM-051 | P0 | Priority-ordered material/property resolution | RM-050 | M | Overlapping primitives test | Implemented |
| RM-052 | P0 | Sub-cell material averaging on edges | RM-051 | L | Partial-fill analytic case | Implemented |
| RM-053 | P0 | Anisotropic eps/mue/kappa/sigma support | RM-050 | M | Per-direction coefficient test | Implemented |
| RM-054 | P0 | Fix `EC_G`/`EC_R` units (remove `EPS0`) | RM-050 | S | Coefficient comparison with native; lossy-medium test | Implemented |
| RM-055 | P0 | Metal/PEC edges and caps | RM-050 | M | PEC cavity test; native comparison | Implemented |
| RM-056 | P1 | Wire Debye/Lorentz operator+engine extensions | RM-041 | L | Dispersive slab differential case | Not Started |
| RM-057 | P1 | Wire conducting-sheet extension | RM-041 | M | Conducting-sheet reference case | Not Started |
| RM-058 | P1 | Wire lumped RLC extension | RM-041 | M | Native lumped-port comparison | Not Started |
| RM-059 | P1 | Wire TFSF extension | RM-041 | M | TFSF plane-wave case | Not Started |
| RM-060 | P1 | Wire steady-state extension and end criteria | RM-041 | M | End criteria stops the run; log matches native semantics | Implemented |
| RM-061 | P1 | Cylinder/multigrid: implement or fail loudly (D-02) | RM-047 | L | Either analytic cylinder case or explicit error + exception | Not Started |
| RM-062 | P1 | Engine variants: multithread first; SSE decision (D-02) | RM-049 | L | Threaded run matches single-thread within tolerance; ADR for SSE | Not Started |
| RM-063 | P1 | Wire `over_sampling`, `max_time`, thread count, abort | RM-041 | M | Each option has an observable effect or an error | Not Started |
| RM-064 | P0 | Remove fabricated default grid; require CSX or an explicit opt-in | RM-004 | S | No geometry produces a clear error | Implemented |
| RM-065 | P0 | Analytic differential suite: 1-D sheet, 3-D coax, MSL, dipole + non-uniform + anisotropic | RM-047..RM-055,RM-043 | L | Recorded tolerances and results in `VALIDATION.md` | Not Started |
## WS5 - Processing and post-processing

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-066 | P0 | Add `EngineInterface` and pass it to processing | RM-065 | M | Probe can read fields from a running engine | Implemented |
| RM-067 | P0 | Implement time-domain `FieldProbe` sampling | RM-066 | S | Signal matches a point sample | Implemented |
| RM-068 | P0 | Implement running DFT probe with frequency list | RM-066 | M | Sinusoid amplitude/frequency test | Implemented |
| RM-069 | P1 | Implement `ProcessIntegral` | RM-066 | S | Analytic integral case | Implemented |
| RM-070 | P1 | Implement `ProcessVoltage`/`ProcessCurrent` | RM-066 | M | Port voltage/current comparison | Implemented |
| RM-071 | P0 | Implement `ProcessFieldsTD` with real dumps | RM-066 | M | Native TD dump comparison | Implemented |
| RM-072 | P0 | Implement `ProcessFieldsFD` with oversampling | RM-066 | L | Native FD dump comparison | Implemented |
| RM-073 | P0 | Implement SAR with 1 g/10 g averaging | RM-066 | L | Native SAR comparison | Not Started |
| RM-074 | P0 | Port native NF2FF transform | RM-066 | XL | Far-field comparison with native reference | Not Started |
| RM-075 | P1 | Implement `ProcessModeMatch` | RM-066 | L | Waveguide mode case | Not Started |
| RM-076 | P0 | HDF5 writer with native datasets/attributes/layout | RM-066 | L | Native Python reader accepts Rust output | Implemented |
| RM-077 | P0 | HDF5 reader and round-trip for native files | RM-076 | L | Rust reads native dumps; values match | Implemented |
| RM-078 | P0 | VTK writer with real mesh/dimensions/vectors | RM-066 | M | ParaView-readable; native comparison | Implemented |
| RM-079 | P0 | Dump scheduling, naming, flush/close semantics | RM-066 | M | File sequence matches native for a short run | Implemented |
| RM-080 | P1 | Implement Python `HDF5Dump`, `readSAR`, NF2FF readers | RM-076 | M | Synthetic + native file tests | Not Started |
| RM-081 | P0 | File-level differential tests and fixtures | RM-076..RM-079 | L | Recorded comparison report | Not Started |
| RM-082 | P2 | Document file formats and compatibility guarantees | RM-081 | S | Doc section with dataset/attribute list | Not Started |
## WS6 - Scripting interfaces

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-083 | P0 | Make Rust CLI accept the native `openEMS` invocation contract | RM-065 | L | Native M-file `RunOpenEMS` drives the Rust binary | Not Started |
| RM-084 | P0 | Match CLI options, exit codes, log files, verbosity | RM-083 | M | Side-by-side invocation log | Not Started |
| RM-085 | P0 | Build native Python package layout | RM-013 | M | `import CSXCAD`, `import openEMS` from installed prefix | Not Started |
| RM-086 | P0 | Match Controller method surface, defaults, errors | RM-085 | L | Native `test_*.py` controller tests pass | Not Started |
| RM-087 | P0 | Implement Python port classes | RM-085 | L | Port tests pass | Not Started |
| RM-088 | P0 | Implement Python NF2FF module | RM-074,RM-085 | L | NF2FF tests pass | Not Started |
| RM-089 | P1 | Implement Python automesh and utilities | RM-085 | L | Automesh/utility tests pass | Not Started |
| RM-090 | P0 | Raise CSXCAD Python classes to native surface | RM-031 | L | Native CSXCAD Python suite passes | Not Started |
| RM-091 | P0 | Make native MATLAB/Octave M-file suite work through CLI | RM-083 | L | 10 suite cases + 2 smoke tests pass | Not Started |
| RM-092 | P0 | Match MATLAB `calcPort`, `CalcNF2FF`, post-processing | RM-091,RM-074 | L | Port/NF2FF comparisons recorded | Not Started |
| RM-093 | P1 | Implement CSXCAD MATLAB M-file surface | RM-032 | L | 58 public + 12 private M-files resolve | Not Started |
| RM-094 | P1 | Match error identifiers, ownership, array orientation | RM-090,RM-093 | M | Contract tests from the interface audits | Not Started |
| RM-095 | P0 | Run native Python suite (31 tests + 150 CSXCAD) unchanged | RM-085..RM-090 | M | Recorded pass counts | Not Started |
| RM-096 | P0 | Run native Octave suite and MSL smoke tests unchanged | RM-091..RM-093 | M | Recorded pass counts | Not Started |
## WS7 - GUI

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-097 | P1 | Render every primitive type, transform and parameter | RM-006 | L | Visual QA against native screenshots | Not Started |
| RM-098 | P1 | Structure tree with properties and primitives | RM-097 | M | Manual checklist | Not Started |
| RM-099 | P1 | Property/material/excitation editor | RM-097 | L | Edit round-trip via XML | Not Started |
| RM-100 | P1 | Primitive add/delete/modify operations | RM-099 | L | Edit/save/load equality | Not Started |
| RM-101 | P1 | Mesh line and parameter editing | RM-099 | M | Grid round-trip | Not Started |
| RM-102 | P2 | Undo/redo and keyboard shortcuts | RM-100 | M | Manual checklist | Not Started |
| RM-103 | P1 | File I/O, settings, CLI arguments parity | RM-098 | M | Native argument/settings comparison | Not Started |
| RM-104 | P1 | Real VTK/STL/PLY/POV/X3D exports from the model | RM-100 | L | Files open and contain the loaded geometry | Not Started |
| RM-105 | P2 | PNG capture from the wgpu frame | RM-097 | M | Non-placeholder image matches the view | Not Started |
| RM-106 | P1 | Manual GUI QA checklist and sign-off | RM-097..RM-105 | S | Signed checklist | Not Started |
## WS8 - hyp2mat and CTB

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-107 | P1 | Build a `.hyp` fixture corpus from native examples/docs | RM-004 | M | Fixtures stored with hashes | Not Started |
| RM-108 | P1 | Implement polygon edge/boolean operations | RM-107 | L | Geometry comparison with native output | Not Started |
| RM-109 | P1 | Match CSXCAD XML output | RM-108 | M | Native CSXCAD reads Rust output; model comparison | Not Started |
| RM-110 | P2 | Match QucsStudio and PDF output | RM-108 | M | Structural/numeric comparison; layer coverage | Not Started |
| RM-111 | P1 | Match hyp2mat CLI options/behavior | RM-109 | S | Side-by-side help and conversion logs | Not Started |
| RM-112 | P1 | CTB per-port reference impedance vectors | RM-004 | M | 3-port `[50;75;60]` round-trip matches MATLAB | Not Started |
| RM-113 | P1 | Complete CTB transform set and dimensions | RM-112 | L | 2-/3-port S/Y/Z/ABCD round-trips | Not Started |
| RM-114 | P1 | Touchstone v1/v2 read/write parity | RM-112 | L | Native files round-trip; edge cases | Not Started |
| RM-115 | P1 | CTB network operations parity | RM-113 | M | Probe cases from the audit | Not Started |
| RM-116 | P1 | CTB delivery form for MATLAB/Octave | RM-112 | L | M-file/MEX or CLI path exercised | Not Started |
## WS9 - Validation and CI

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-117 | P0 | Build differential harness over `reference-data/` | RM-065 | L | Harness runs and reports per-case deltas | Not Started |
| RM-118 | P0 | Execute all reference cases through the harness | RM-117,RM-066 | M | Result table with pass/fail | Not Started |
| RM-119 | P0 | Approve and record tolerances | RM-118 | S | Tolerance table with justification | Not Started |
| RM-120 | P1 | Cross-platform runtime CI (Linux/Windows/macOS/FreeBSD) | RM-017,RM-117 | L | Platform result matrix | Not Started |
| RM-121 | P2 | Performance baseline vs native | RM-065 | M | Solver time/throughput table | Not Started |
| RM-122 | P2 | Memory baseline vs native | RM-065 | M | Peak RSS table | Not Started |
| RM-123 | P1 | Regression CI for unit + integration suites | RM-117 | M | Required check on PRs | Not Started |
| RM-124 | P2 | Nightly reference run | RM-123 | M | Nightly artifact | Not Started |
| RM-125 | P0 | Full-stack acceptance run | RM-095,RM-096,RM-118,RM-123 | L | Recorded acceptance report | Blocked |
| RM-126 | P0 | Exception register (approved omissions) | RM-006 | S | Every exception has impact + native compatibility path | Verified |
| RM-127 | P0 | Final audit against `AGENTS.md` Section 21 | RM-125 | M | Signed checklist, no unverified `Verified` rows | Blocked |
## WS10 - Documentation and status

| ID | Pri | Task | Depends | Est | Acceptance / Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RM-128 | P0 | Correct Tasks 17-19 statuses in `TASKS.md` | RM-006 | S | Status matches the finding register | Verified |
| RM-129 | P0 | Convert `COVERAGE_MATRIX.csv` to the closed status vocabulary | RM-006 | M | Every row has one of the six statuses + evidence | Verified |
| RM-130 | P0 | Rebuild `VALIDATION.md` counts/evidence from actual runs | RM-125 | M | Counts match executed commands | Verified |
| RM-131 | P0 | Update `MIGRATION_STATUS.md` and session records | RM-128..RM-130 | S | No claim without evidence | Verified |
| RM-132 | P1 | Write ADRs for D-01..D-07 | RM-001..RM-006 | M | One ADR per decision under `docs/adr/` | Verified |
| RM-133 | P2 | Add docs consistency check to CI | RM-129 | S | CI rejects stale counts/statuses | Verified |
---

## Gate checklists

### G0 - Consolidation
- [ ] D-01 decision recorded (RM-001)
- [ ] Duplicate tree archived (RM-002)
- [ ] Submodule commits reachable from pushed branches (RM-003)
- [ ] Root pointers bumped after push (RM-004)
- [ ] Root workspace artifacts committed (RM-005)
- [ ] Status policy published (RM-006)

### G1 - Installable
- [ ] Clean-prefix install on Linux and Windows (RM-017)
- [ ] `import CSXCAD`, `import openEMS` from installed prefix (RM-013)
- [ ] Advertised binaries exist and run (RM-014, RM-015)
- [ ] MATLAB M-files resolve (RM-016)

### G2 - Solver correctness
- [ ] Excitation arrays match native (RM-037, RM-038)
- [ ] Extensions registered and ordered (RM-041)
- [ ] Mesh/material/EC fixes verified (RM-047..RM-055)
- [ ] Differential cases pass with approved tolerances (RM-065, RM-117, RM-118, RM-119)

### G3 - I/O
- [ ] Native readers accept Rust output (RM-076)
- [ ] Rust reads native output (RM-077)
- [ ] NF2FF/SAR comparisons pass (RM-073, RM-074)

### G4 - Interfaces
- [ ] Native Python suite passes (RM-095)
- [ ] Native Octave suite + smoke tests pass (RM-096)

### G5 - GUI / converters
- [ ] GUI QA signed (RM-106)
- [ ] hyp2mat fixtures match (RM-109, RM-110)
- [ ] CTB comparisons match (RM-113..RM-115)

### G6 - Acceptance
- [ ] Full-stack run recorded (RM-125)
- [ ] Exceptions registered (RM-126)
- [ ] Final `AGENTS.md` Section 21 audit signed (RM-127)
- [ ] Docs consistent (RM-128..RM-133)

---

## Progress evidence

Record the command, its output and the reference for every status change.
`Implemented` means the code path exists and is tested at unit level;
`Verified` additionally requires the differential/reference comparison named
in the task's acceptance column.

| Date | Task(s) | Status | Evidence |
| --- | --- | --- | --- |
| 2026-10-24 | RM-001 | Verified | `docs/adr/0001-canonical-rust-tree.md`: canonical tree is the `mberkanbicer-rust-migration-audit` worktree; the 3-crate root `rust/` tree is frozen |
| 2026-10-24 | RM-037, RM-038, RM-039 | Implemented | `openEMS/rust/src/excitation.rs` builds native voltage/current sample arrays (Gaussian/Sinus/Dirac/Step/Custom), Nyquist count and max-timestep; the excitation and TFSF extensions read `voltage()`/`current()`. Command: `cargo test -p openems-core` -> 124 passed. Differential comparison against native arrays is still RM-065 |
| 2026-10-24 | RM-050 | Implemented | `material_grid` is `3*nx*ny*nz`, initialized from the background material, and primitives fill all three directions; `test_load_csx_material_grid_populated` asserts the PEC and substrate cells in every direction. Priority ordering and edge averaging remain RM-051/RM-052 |
| 2026-10-24 | RM-054 | Implemented | `EC_G = kappa*area/len` and `EC_R = sigma*area/len` (no `EPS0` factor) in `calc_ec_operator`, `calc_ec_pos` and `ec_coefficients_use_native_conductivity_units`; differential comparison is still RM-065 |
| 2026-10-24 | RM-045, RM-046 | Implemented | `apply_electric_bc` / `apply_magnetic_bc` now zero only the two tangential components per face; `pec_boundary_zeroes_only_tangential_components` and `pmc_boundary_zeroes_only_tangential_components` assert the normal component stays nonzero. Command: `cargo test -p openems-core` -> 126 passed |
| 2026-10-24 | RM-041, RM-044 | Implemented | `Operator::build_excitation_extension` maps CSXCAD Excitation properties to Yee edges (priority, active direction, soft/hard type, weighted amplitude, delay); `Operator::build_mur_extension` computes native per-face Mur coefficients; `OpenEMS::setup_fdtd` registers both. `excitation_property_injects_field_end_to_end` asserts a nonzero field after a real run; `mur_extension_builds_six_faces` and `test_mur_three_phase_update_matches_native_sequence` cover Mur. Command: `cargo test -p openems-core` -> 132 passed. Not all physics extensions are registered yet (UPML, dispersive, TFSF, lumped, sheet). The XML AbsorbingBC face selection still applies the sign to all three axes and needs native geometry-based selection |
| 2026-10-24 | RM-047, RM-048 | Implemented | `disc_lines`/`grid_delta` retain the native drawing-unit representation; `GetEdgeLength`/`GetEdgeArea`/`GetNodeWidth`/`GetCellVolume` use real (possibly non-uniform) spacing; `calc_ec_operator` uses per-direction primary/dual geometry. `nonuniform_mesh_edge_lengths_and_ec_coefficients` checks 1/2/3 mm spacing, area and the c_x/c_y ratio |
| 2026-10-24 | RM-051 | Implemented | Edge materials resolve the highest-priority containing primitive per direction; `material_priority_and_containment_select_the_right_edge` checks low/high box and sphere priority plus non-bounding-box sphere containment. Sub-cell quarter-cell averaging (RM-052) is still open; the current sample is the edge midpoint |
| 2026-10-24 | RM-055 | Implemented | Metal edges set `is_pec` and `calc_ec_operator` zeroes their `vv`/`vi`; `metal_edges_zero_the_electric_update` asserts inside/outside values |
| 2026-10-24 | RM-064 | Implemented | `setup_fdtd` now requires a CSX geometry (`setup_without_geometry_fails`); a configured PML returns a loud error instead of a silent no-op. Var3 (RM-049), UPML (RM-042/043) and the remaining option wiring (RM-063) are still open |
| 2026-10-24 | RM-063 (partial) | Not Started | `max_time`, explicit `time_step`, `time_step_factor` and the timestep-method guard are wired and tested (`max_time_limits_the_run`, `timestep_factor_scales_the_cfl_step`); `over_sampling`, `enable_dumps` and the thread count still have no effect |
| 2026-10-24 | RM-037/038/041 (bug fix) | Implemented | Timestep ordering fixed: `calc_timestep` now runs before `calc_ec_operator`. Previously the coefficients were built with `dt = 0`, leaving `vi`/`iv` zero and preventing any wave propagation. `excitation_property_injects_field_end_to_end` now also asserts that the neighbouring cell is nonzero. `cargo test -p openems-core` -> 135 passed |
| 2026-10-24 | RM-042/043 | Implemented | UPML is now enabled. `setup_fdtd` builds the six layer regions, rewrites the main `vv`/`vi`/`ii`/`iv` inside the layer like `Operator_Ext_UPML::BuildExtension`, registers the engine flux extension, and defaults a PML face to 8 cells. `upml_absorbs_a_gaussian_pulse` measures a 6 GHz pulse in a 41x21x21 mm box with 8-cell PML: residual/peak = 1.4e-6 (-117 dB) versus 1.3e-2 for the PEC reference. `setup_fdtd_accepts_pml_and_defaults_to_eight_cells` and `setup_fdtd_rejects_a_pml_larger_than_the_mesh` cover the wiring. A coefficient-by-coefficient comparison against a native PML box is still outstanding |
| 2026-10-24 | RM-049 | Implemented | `calc_timestep_var1` and `calc_timestep_var3` implement `Rennings_1`/`Rennings_2`, `calc_timestep` dispatches on `m_time_step_var`, and `setup_fdtd` maps `time_step_method` (0/1 -> Var1, 3 -> Var3). Node shifts use the native `AdrOp` reflection formula. `var1_and_var3_match_the_uniform_mesh_analytic_values` checks Var1 = delta/(2c) and Var3 = delta/(sqrt(3)c) to 1e-6, and Var3 > Var1 on a non-uniform mesh |
| 2026-10-24 | RM-052 | Implemented | `load_csx` now performs native quarter-cell averaging: epsilon/kappa as an area-weighted arithmetic mean over the four transverse quarter cells, mue/sigma as a width-weighted harmonic mean along the edge, PEC from the single Yee-edge coordinate. `quarter_cell_averaging_matches_the_analytic_half_space` checks the exact 2.5 average at the interface, 4.0 inside and 1.0 outside; `material_priority_and_containment_select_the_right_edge` was updated to the averaged values |
| 2026-10-24 | RM-072 | Implemented | `ProcessFieldsFD` accumulates a running DFT with the native Nyquist/oversampling interval, exposes real/imag parts, and dumps VTK magnitude, phase and 21 phase snapshots or the native HDF5 `f0..fn` real/imag pairs with `frequency` attributes. `frequency_domain_accumulates_a_known_tone` verifies the N/2 amplitude and >100x off-bin rejection; `frequency_domain_dump_writes_native_hdf5_layout` checks the file |
| 2026-10-24 | RM-076, RM-077 | Implemented | New `hdf5` module (system HDF5 C API, `hdf5` feature + `build.rs`) replaces the private `OHDF` file format. Writer covers `/Mesh` + `mesh_type`/`mesh_scaling`, `/FieldData/TD/<8 digits>` + `time`, `/FieldData/FD` + `frequency`, legacy `_real`/`_imag` pairs, `d_order`, and the root metadata attributes. Reader covers datasets, compound complex, scalar/vector/string attributes and link listing. `reads_a_native_openems_dump` opens the recorded C++ dump `reference-data/msl-notchfilter-wsl/field-run-1/Et_ref.h5` (mesh 5x5x1, 10 TD steps, `d_order=NXYZ`, `time=1.774336e-11`); `round_trips_the_native_field_layout` covers write-back. Verified on Windows against HDF5 1.14 (FreeCAD import lib); the native Python reader check and coefficient-level PML comparison remain open |
| 2026-10-24 | RM-066, RM-067 | Implemented | `EngineMeta`/`EngineInterface`, `Processing::process_fields`, `ProcessingArray::process_fields`; `run_fdtd` passes the live voltage/current arrays and `FieldProbe` records samples at the nearest mesh index. Tests: `field_probe_samples_engine_fields`, `run_fdtd_drives_processing_fields`. `cargo test -p openems-core` -> 137 passed. Running DFT accumulation (RM-068) and file dumps remain open |
| 2026-10-24 | RM-068 | Implemented | `FieldProbe` now stores a frequency list and a running DFT (`ComplexPoint`), accumulates `sample*exp(-j2*pi*f*t)` on every processed step, deduplicates frequencies, and resets accumulators. `field_probe_accumulates_dft` verifies on-bin amplitude N/2 and >100x off-bin rejection over 10 periods. `cargo test -p openems-core` -> 138 passed |
| 2026-10-24 | RM-071, RM-078 | Implemented | `VTKFileWriter::write_structured_grid` emits a real structured grid (explicit points, real dimensions, vector field); `ProcessFieldsTD::process_fields` writes `name_<ts>.vtk` from the live E or H field at the configured interval/steps. `process_fields_td_writes_real_vtk` checks header, dimensions, points and vector values. HDF5 dumps (RM-076) and native differential comparison remain open; `cargo test -p openems-core` -> 139 passed |

| 2026-10-25 | RM-002 | Verified | Frozen three-crate tree archived as tag `archive/rust-3crate-tree-2026-10` at root `a56e922` and pushed to origin; its submodule SHAs are recorded in ADR 0001. The canonical tree contains exactly one `fparser-rs`, `csxcad-core` and `openems-core` package (checked with a recursive `Cargo.toml` name scan) |
| 2026-10-25 | RM-003 | Verified | All seven submodules now have branch `mberkanbicer-rust-migration-audit` pushed to their own origin; `git branch -r --contains HEAD` lists that branch for fparser, CSXCAD, openEMS, QCSXCAD, AppCSXCAD, hyp2mat and CTB |
| 2026-10-25 | RM-004 | Verified | Root pointer bump committed after the pushes; `git submodule status` shows the pushed CSXCAD `5429817` and openEMS `5dde9c4` revisions and the remaining five at their branch heads |
| 2026-10-25 | RM-005 | Verified | Root `Cargo.toml` (13 members plus `default-members` without the PyO3 crates), `Cargo.lock`, `.gitignore` and `.gitattributes` (`*.sh text eol=lf`) committed; generated `diff.txt`, `rust/output.h5`, `rust/output.vtk` and `rust-py/target/` removed or ignored; `git status` clean |
| 2026-10-25 | RM-006 | Implemented | Status/evidence policy published as Section 0 of `REMEDIATION_PLAN.md` and repeated in `MIGRATION_STATUS.md`: six-value vocabulary, evidence rule, tolerance rule, exception register, and 'task list is authoritative'. Team acknowledgement is the owner review of this change |
| 2026-10-25 | RM-007 | Implemented | `scripts/ci/check_placeholders.py` flags `todo!`, `unimplemented!`, placeholder/stub markers and not-implemented panics in changed Rust files, supports a reviewed allowlist and has a passing `--self-test`; the Rust workflow runs it on every push and PR |
| 2026-10-25 | RM-008 | Implemented | Remediation register, progress log and task statuses are maintained in this file; each change that moves a task adds an evidence row |
| 2026-10-25 | RM-009 | Verified | One `rust-workspace` CMake target builds the root Cargo workspace with a shared target directory; the 13 per-crate ExternalProjects were removed. `cmake --build --target rust-workspace` finished in 1m50s on Windows and 3m25s in WSL; `cmake --install` produced `bin/openEMS`, `bin/AppCSXCAD`, `bin/hyp2mat`, the two MATLAB libraries and the native `share/` layout on both platforms |
| 2026-10-25 | RM-010 | Implemented | `update_openEMS.sh` now passes `-DBUILD_RUST`/`-DBUILD_RUST_PYTHON` to CMake and verifies `bin/openEMS`, `share/openEMS/matlab` and `share/CSXCAD/matlab` after install; the per-crate cargo block was removed. Bash syntax checked in WSL; the end-to-end script run needs the C++ stack and is not executed here |
| 2026-10-25 | RM-011 | Verified | `scripts/install_deps.sh --with-rust` checks cargo/rustc (and maturin with `--python`) with rustup instructions; `bash scripts/install_deps.sh --check --with-rust --disable-gui` reports all dependencies present in WSL |
| 2026-10-25 | RM-012 | Verified | PyO3 upgraded 0.23 -> 0.30 (CPython 3.14 support) with a two-line binding fix; `maturin build` produced `csxcad_python-0.1.0-cp314-cp314-win_amd64.whl` and `openems_py-0.1.0-cp314-cp314-win_amd64.whl`; both installed into a fresh venv and `import csxcad_py, openems_py` succeeds. CMake exposes `BUILD_RUST_PYTHON` and `RUST_PYTHON` |
| 2026-10-25 | RM-014 | Verified | CTB is delivered as a library plus the MATLAB/Octave path; no standalone binary is required. The decision and its compatibility path are recorded as exception E-002 in `EXCEPTIONS.md`, and the install layout advertises no `ctb` binary |
| 2026-10-25 | RM-016 | Verified | `cmake --install` installs the native M-files to `share/openEMS/matlab` and `share/CSXCAD/matlab` and the C ABI libraries to `lib/` on Windows (`csxcad_matlab.dll`, `openems_matlab.dll`) and Linux (`libcsxcad_matlab.so`, `libopenems_matlab.so`) |
| 2026-10-25 | RM-017 | Verified | Clean-prefix verification recorded for both platforms: Windows (VS 2022 generator, configure/build/install, file listing) and WSL Ubuntu (CMake 4.2.3, gcc 15.2, cargo 1.99, `openEMS --version` and `hyp2mat --help` executed from the installed prefix). The C++ ExternalProject builds are outside the Rust scope and were not run |
| 2026-10-25 | RM-018 | Implemented | Linux CI job in `.github/workflows/rust.yml`: workspace check, numerical suite, placeholder policy and migration-record gate |
| 2026-10-25 | RM-019 | Implemented | Windows CI job runs `cargo check --workspace`, the numerical suite and the placeholder self-test |
| 2026-10-25 | RM-020 | Implemented | macOS job runs workspace check plus the numerical suite; a FreeBSD job runs `cargo check --workspace` in a VM. Both are defined but can only be confirmed by the first CI run |
| 2026-10-25 | RM-021 | Implemented | Single entry point documented: CMake builds and installs the Rust workspace when `-DBUILD_RUST=YES`; `update_openEMS.sh --with-rust` only sets that flag and verifies the result. The per-crate build loops are gone from both CMake and the script |
| 2026-10-25 | RM-022 | Implemented | Build/install documentation updated in `docs/migration/VALIDATION.md` (feature flags, HDF5 import library, wheel build, prefix layout) and in the script help text |
| 2026-10-25 | RM-125 | Blocked | Full-stack acceptance depends on RM-095/RM-096 (native Python/Octave suites) and RM-118/RM-123 (reference runs and regression CI), which are still `Not Started`. Not claimed |
| 2026-10-25 | RM-127 | Blocked | Final `AGENTS.md` Section 21 audit depends on RM-125. Not claimed |
| 2026-10-25 | RM-126 | Verified | `docs/migration/EXCEPTIONS.md` records E-001 (fparser f64 only, ADR 0006), E-002 (CTB delivery form), E-003 (system HDF5) and E-004 (egui/wgpu GUI), each with impact and compatibility path |
| 2026-10-25 | RM-128 | Verified | `tasks/todo.md` Tasks 17-19 changed from `Done` to `Implemented (remediation tracked)` with explicit open-item corrections, plus a status-correction note that the remediation task list is authoritative |
| 2026-10-25 | RM-129 | Verified | `COVERAGE_MATRIX.csv` gained a closed-vocabulary `Status` column (28 rows: 20 Implemented, 8 Not Started); the free-text column is retained as `Implementation Notes` |
| 2026-10-25 | RM-130 | Verified | `VALIDATION.md` counts rebuilt from executed commands: fparser 52, CSXCAD 148, openEMS 159 + 2 integration, hyp2mat 14 (375 total) and openEMS 162 + 2 with `--features hdf5`; the Wave A build/install and wheel transcripts are appended |
| 2026-10-25 | RM-131 | Verified | `MIGRATION_STATUS.md` opening status rewritten to the canonical branch, pushed pointers, archive tag, current counts and the open areas; it now defers to the task list for live counts |
| 2026-10-25 | RM-132 | Verified | ADRs 0001-0007 written for D-01..D-07 (canonical tree, engine/boundary scope, system HDF5, egui/wgpu, MATLAB via CLI, fparser f64 only, tolerance approval) |
| 2026-10-25 | RM-133 | Verified | `scripts/ci/check_migration_docs.py` validates the closed vocabulary, snapshot counts, backlog header and coverage-matrix statuses; it passes locally and runs in the Linux CI job |

| 2026-10-25 | RM-060 | Implemented | Steady-state detection completed and wired: `EngineExtSteadyState` now includes the native `CalcFastEnergy` term, starts at 1.0, bounds-checks probes and exposes the native probe layout (centre plus quarter/three-quarter on each axis, all components); `Operator::build_steady_state_extension` creates it for periodic excitations and `setup_fdtd` registers it. `run_fdtd` uses the extension metric when present and otherwise the native `currE / maxE` energy criterion, which also removes the infinite-loop case when `nr_ts` and `max_time` are both zero. Fixed a real compatibility bug: periodic excitations were not repeated (`Engine_Ext_Excitation` wraps the sample index modulo the period), so sinusoidal sources stopped after two periods. Tests: `steady_state_extension_uses_the_native_probe_layout` (21 probes), `energy_term_detects_a_decaying_field`, `periodic_excitation_registers_steady_state_detection`, `steady_state_end_criteria_stops_a_periodic_run_early` (stops at 240 of 4000 steps), `aperiodic_excitation_uses_the_energy_end_criteria`, `periodic_sources_repeat_every_period` |

## Change log

| Date | Change |
| --- | --- |
| 2026-10-24 | Initial task list created from the remediation audit |
| 2026-10-24 | Added Status column and first progress evidence (RM-001, RM-037..039, RM-050, RM-054) |
| 2026-10-24 | RM-053 | Implemented | CSXCAD now infers anisotropy from per-direction `Property` vectors (`Epsilon="2,4,6"`) unless an explicit `Isotropy` attribute is present (`vector_material_attributes_are_anisotropic`, `equal_vector_components_stay_isotropic`, `explicit_isotropy_attribute_wins_over_vector_length`). `operator::anisotropy_tests::anisotropic_epsilon_scales_each_edge_direction` checks that the EC capacitance follows each direction (vi_x:vi_y:vi_z = 1/2:1/4:1/6) |
| 2026-10-24 | RM-065 (partial) | Not Started | New integration suite `openEMS/rust/tests/analytic_validation.rs`: vacuum pulse speed measured 2.9404e8 m/s vs c (1.9% error, tolerance 3%) and dielectric speed c/2 within 1.0%. The remaining cases (1-D sheet, 3-D coax, MSL, dipole, non-uniform/anisotropic propagation) are still open, so the task stays `Not Started` |
| 2026-10-24 | RM-069, RM-070 | Implemented | New `processing_integral` module: `ProcessIntegral` streams native-format TD rows (`% t/s`, one row per processed step, `weight`/`precision` honoured) and a `<filename>_FD` table of the running DFT; `IntegralCalculator` is the native `CalcMultipleIntegrals` hook. `VoltageIntegral` sums the line voltages and `CurrentIntegral` walks the surface perimeter exactly like `ProcessCurrent` (all three normal directions). Tests: `integral_streams_analytic_td_rows_and_matches_the_dft_sum`, `voltage_integral_sums_the_line_voltages`, `current_integral_walks_the_surface_perimeter` |
| 2026-10-24 | RM-079 | Implemented | `ProcessFieldsTD` honours `set_sub_sampling`/`set_opt_resolution` per axis (native `CalcMeshPos` semantics; the direction argument was previously ignored), writes the native 10-digit VTK sequence (`<name>_0000000002.vtk`) and the 8-digit HDF5 dataset sequence over the reduced `/Mesh`. Files are opened and closed per dump, so every file is flushed. Tests: `sub_sampling_and_optical_resolution_reduce_the_dump_mesh`, `time_domain_dump_writes_the_native_timestep_sequence`, `time_domain_dump_sub_sampling_changes_the_written_grid` |
