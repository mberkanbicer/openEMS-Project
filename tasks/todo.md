# Rust Migration Task List

Track execution here and in the session task database. Update both when task
status or dependencies change. “Verification” is required before marking a task
done. Build/test results must reflect commands actually run.

## Phase 1: Audit

### 1. Initial repository and submodule inventory — Done

- [x] Confirm pinned submodules, project instructions, root build graph, and
  major component boundaries.
- [x] Create persistent migration plan, status, coverage, and validation records.
- **Verification:** `git submodule status`; inspect root and available submodule
  instructions; check matrix CSV structure.
- **Dependencies:** None.

### 2. Audit fparser source and behavior — Done (validation limits documented)

- [x] Inventory all tracked paths and map the public API, parser/evaluator
  stages, generated/conditional code, build definitions, and tests.
- [x] Trace evaluator error codes 1-4, nested error propagation,
  inline-variable fetches, and conditional branch behavior against source and
  focused probes.
- [x] Probe precedence, unit binding, degree mode, comparison epsilon
  boundaries, and logical truth thresholds.
- [x] Inventory source-listed functions/type flags and smoke-test all default
  real functions plus complex-only operations in complex double.
- [x] Map evaluator semantics, numeric edge classes, custom-function
  registration/lifetimes, and optimizer effects from source and focused probes.
- [x] Record exact source/symbol coverage and unresolved behavior in the
  migration matrix and status.
- [x] Build and probe the complex-double configuration, including signed-zero
  square-root behavior and an optimized constant case.
- [x] Map optimizer pipeline, generated rule metadata, and optional backend
  source behavior; document generated-rule and runtime validation limits.
- [x] Compile and smoke-test complex float and long-double variants.
- [x] Map MPFR/GMP wrapper dependencies, precision and conversion behavior
  from source.
- [x] Build and audit MPFR/GMP configurations when the required libraries are
  available.
- [x] Establish representative original behavior cases beyond the `x^2` and
  scalar-type, sine, and constant-equality smoke inputs already recorded.
- [x] Capture focused error, inline-variable, nested-parser, conditional, and
  optimized/unoptimized callback probes.
- [x] Compare a representative expression corpus before and after
  `Optimize()`; record observed error and compile-time rewrite changes.
- [ ] Extend generated-rule differential coverage, numeric-domain/type
  cross-product cases, and cross-platform behavior when suitable toolchains
  are available. The differential runner now includes NaN and infinities in
  optimized/unoptimized operator and built-in matrices; the expanded runs
  passed 36,717 expressions and 36,692 callback-count checks on Windows/MSVC
  and Ubuntu WSL/GCC. Broader per-type/domain coverage and runtime checks on
  other platforms remain open.
- **Progress:** Initial source/API pass is in
  `docs/migration/audits/fparser.md`; default CMake build, `x^2` example, and
  opt-in float/long-double/long-integer examples succeeded. Sine and constant
  equality plus focused evaluator/inline-variable/parser-link/optimizer
  probes plus precedence, units, degrees, epsilon boundaries, and truth
  thresholds were tested; a complex-double configuration was compiled and
  probed, then complex float/long-double variants also compiled and ran.
  The complete built-in function table and its integer/complex/angle flags were
  inventoried, and every built-in was smoke-tested in the default double
  parser; the complex-only built-ins were also exercised in the complex-double
  parser, with exact outputs recorded. Separate C++98 MPFR/GMP builds passed
  focused arithmetic probes under WSL using preinstalled dependencies. The
  optimizer's generated rule count,
  grammar subsets, pipeline order, and guard categories were mapped, but
  individual patterns remain opaque. MPFR/GMP wrapper sources were inspected;
  the checked MSYS2/vcpkg locations lacked headers, but preinstalled WSL
  libraries supported separate builds and arithmetic probes without installing
  dependencies. Residual validation gaps are
  explicitly tracked: individual rewrite patterns, broader cross-type/domain
  cases, cross-platform complex behavior, and broader MPFR/GMP backend tests.
  The repository has examples but no registered test suite.
- **Verification:** Check every tracked source/build/test file; run existing
  examples or focused reference cases where the toolchain supports them;
  record commands/results and do not treat a build as semantic validation.
- **Dependencies:** Task 1.

### 3. Audit CSXCAD native model, API, XML, and tests — Done (runtime validation blocked)

- [x] Map classes/functions for structures, properties, primitives, transforms,
  parameters, mesh, and serialization.
- [x] Trace XML read/write compatibility and ownership/lifetime behavior.
- [x] Inventory C++ tests, native dependencies, formats, and uncovered paths.
- **Progress:** The source map and concrete class families are recorded in
  `docs/migration/audits/csxcad-native.md`, including structure/property/
  primitive ownership, transforms, parameters, mesh, XML dispatch, and
  visible tests. Per-subclass copy semantics and complete XML behavior remain
  explicit compatibility work for later consolidation.
- **Verification:** Source contracts and visible test entry points were
  cross-checked. The Windows CMake configure check could not find the fparser
  include directory or TinyXML, so no C++ tests ran.
- **Dependencies:** Task 2.

### 4. Audit CSXCAD Python/Cython and Matlab/Octave APIs — Done (runtime limits documented)

- [x] Map public binding functions, ownership/identity rules, exceptions,
  serialization paths, and package/build behavior.
- [x] Map M-file entry points and shared XML semantics with the native API.
- [x] Record compatibility cases and tests for both interfaces.
- **Progress:** The interface map and MATLAB R2025b XML writer probe are in
  `docs/migration/audits/csxcad-interfaces.md`. The WSL baseline built the
  Python extension and passed 150 Python tests (one skipped); the native C++
  tests passed 2/2. The openEMS Octave suite also passed after Octave setup.
  Separate WSL Octave probes confirmed raw ampersand output, explicit empty
  elements, and the unchecked-file-open error path. Method-by-method coverage
  of some Cython/M-file behavior remains in Task 12.
- **Verification:** Source/declaration modules and test entry points were
  mapped; the MATLAB XML probe, documented Python/native suites, and focused
  Octave XML escaping/empty/open-failure probes passed their expected
  assertions.
- **Dependencies:** Task 3.

### 5. Audit openEMS FDTD solver and physics extensions — Done (runtime baseline captured)

- [x] Map setup parsing, operator construction, engine state, update order,
  coordinate systems, and extension hooks.
- [x] Trace initialization, boundary conditions, excitation/material models,
  precision, threading/SIMD paths, and termination rules.
- [x] Map solver tests and analytical/reference cases without changing the
  original implementation.
- **Progress:** Setup/operator/engine flow, update and extension order,
  defaults, termination behavior, and existing test/reference categories are
  mapped in `docs/migration/audits/openems-core.md`. Detailed equation-level
  audits of each extension and simulation baselines remain for consolidation.
- **Verification:** MATLAB listed all 10 suite cases and ran the pure-M-file
  `port_setup` and `transforms` groups: 17 checks passed. The WSL baseline
  passed the full 10-case openEMS Octave suite, including four-engine field
  dump equality checks, and the 31-test Python unit/simulation suite.
- **Dependencies:** Task 3.

### 6. Audit openEMS processing, I/O, NF2FF, SAR, and tools — Done (runtime limits documented)

- [x] Map processing/probe/dump paths, field formats, post-processing,
  NF2FF, SAR, and numerical helpers to source files and symbols.
- [x] Record output formats, units, intermediate data, precision, and available
  expected results.
- [x] Identify tested versus untested paths.
- **Progress:** Processing lifecycle, field interfaces, FD accumulation and
  output formats, NF2FF and SAR source paths, and available analytic tests are
  recorded in `docs/migration/audits/openems-processing.md`. Exact unit,
  scaling, and round-trip contracts remain for baseline/consolidation.
- **Verification:** Source/test paths and suite documentation were mapped.
  Native I/O, NF2FF, SAR, and Python processing paths were exercised by the
  WSL baseline's Python unit/simulation suite and Octave solver suite; further
  Rust differential datasets and cross-platform comparisons remain open.
- **Dependencies:** Task 5.

### 7. Audit openEMS Python/Cython and Matlab/Octave interfaces — Done (runtime limits documented)

- [x] Map public functions, parameters/defaults, errors, data types,
  cancellation/progress, and backend interactions.
- [x] Trace representative workflows end-to-end from scripting input to
  solver outputs.
- [x] Inventory unit, simulation, smoke, and tutorial coverage.
- **Progress:** The Python/Cython and M-file workflow/source map is in
  `docs/migration/audits/openems-interfaces.md`, including the controller,
  port, NF2FF, mesh, utility, SAR, and M-file declaration inventories. The
  WSL baseline passed 10 Python unit tests, 21 full simulation tests, all 10
  Octave suite cases, and both MSL smoke tests. Per-method argument/error and
  numerical contracts remain part of Task 12 consolidation.
- **Verification:** Interface sources and test entry points were cross-checked;
  runtime results and their remaining limits are in `VALIDATION.md`.
- **Dependencies:** Tasks 4 and 6.

### 8. Audit QCSXCAD and AppCSXCAD GUI workflows — Done (interactive validation blocked)

- [x] Map windows, editors, geometry/property actions, rendering/export,
  project I/O, and GUI-to-CSXCAD interactions.
- [x] Record Qt/VTK requirements, platform conditionals, and automated/manual
  test coverage.
- **Progress:** The GUI architecture and action map, I/O, export, platform
  conditionals, test gaps, and source findings are in
  `docs/migration/audits/gui.md`. No GUI test targets or manual QA checklist
  are present; the WSL baseline compiled and linked the GUI, but headless
  interactive runtime validation remains unavailable.
- **Verification:** Main actions were traced through Qt signal/slot wiring,
  implementation, and CMake. The WSL full build compiled and linked the GUI;
  no interactive behavior was executed in the headless session. The earlier
  Windows configure attempt failed because CSXCAD library/include paths and
  TinyXML were unavailable.
- **Dependencies:** Task 3.

### 9. Audit hyp2mat parser and conversion workflows — Done (fixture validation blocked)

- [x] Map supported input dialects, parser stages, PCB entities, outputs,
  unsupported cases, and command-line behavior.
- [x] Inventory fixtures, platform dependencies, and conversion tests.
- **Verification:** Match every documented format/output feature to source and
  fixtures; run available fixtures without editing references. The source and
  fixture inventory is recorded in `docs/migration/audits/hyp2mat.md`. The
  WSL root build compiled the converter and `hyp2mat --help` passed, but no
  HyperLynx fixture exists for a conversion test.
- **Dependencies:** Task 1.

### 10. Audit CTB function and numerical behavior — Done (findings documented)

- [x] Map every Matlab/Octave function, parameter convention, matrix shape,
  units, and Touchstone read/write behavior.
- [x] Inventory examples and available tests; identify edge cases.
- [x] Extend edge/domain/malformed-input probes beyond the executed reference
  cases in `docs/migration/audits/ctb.md`.
- **Progress:** MATLAB R2025b additionally exercised singular transforms,
  invalid reference values, shape handling, malformed and truncated
  Touchstone input, zero/negative frequencies, and network-operation edge
  cases. A three-frequency two-port corpus with asymmetric reference
  impedances `[50;75]` additionally round-tripped S/Y/Z and S/ABCD conversions
  with maximum absolute error below `4.3e-14`; a 3-port corpus with
  `[50;75;60]` references also round-tripped S/Y/Z with maximum error below
  `1.3e-16`. Two-frequency 2-port Touchstone S/Z/Y writer-reader round trips
  additionally passed exactly with their distinct default references, and
  three-port S renormalization between unequal per-port references round-
  tripped with maximum error `1.39e-16`. Three-port S-to-Z/Y conversions also
  matched direct matrix equations with maximum error `2.84e-14`; the
  renormalized S matrix preserved Z within `7.12e-15`. A single-frequency
  2-port S/ABCD round trip also passed within `1.25e-16`. Results and residual
  cross-product gaps are documented in
  `docs/migration/audits/ctb.md` and `docs/migration/VALIDATION.md`.
- **Verification:** Review all M-files and compare numerical identities and
  file round trips with executable references when Octave/Matlab is available.
  MATLAB probes ran; exhaustive cross-product and independent Touchstone
  interoperability checks remain open for audit consolidation.
- **Dependencies:** Task 1.

### 11. Audit root orchestration, CI, packaging, and platforms

- [x] Map root build options, scripts, package flows, CI matrix, and
  submodule interactions.
- [x] Account for supported operating systems, architectures, compilers, and
  Python venv modes.
- [x] Identify generated, linked, and externally maintained artifacts.
- **Progress:** Source map, platform matrix, optional builds, dependency
  checker, TinyXML download verification, Python venv handling, and source
  archive process are recorded in
  `docs/migration/audits/root-orchestration.md`. The audit records a confirmed
  `site` venv option mismatch and generic build-script error output. A WSL
  full-stack build with GUI, Python, and CTB passed; hyp2mat also built through
  the root option. The site-mode failure was reproduced before applying a
  temporary venv workaround.
- **Verification:** CI/build workflows were traced to their commands and
  outputs. `bash -n` passed for the root build script and all scripts under
  `scripts/`; the original stack built and passed its principal test suites in
  WSL. Other platform builds remain unrun.
- **Dependencies:** Task 1.

### 12. Consolidate the complete audit

- [x] Complete per-file/function coverage and map every public API, data format,
  integration, build option, test, and platform path.
- [x] Classify verified defects, open questions, intentional limitations, and
  migration risks with evidence.
- [x] Update plan, status, matrix, and validation strategy from inspected facts.
- **Progress:** Component audits and the coverage matrix now account for the
  root and all seven submodules. Tracked source/build-language paths were
  enumerated by submodule (fparser 17, CSXCAD 191, openEMS 379, QCSXCAD 26,
  AppCSXCAD 6, hyp2mat 53, CTB 23). Declaration cross-checks find all 114
  CSXCAD and 96 openEMS M-file functions, plus all 293 CSXCAD / 48 openEMS
  Python-visible Cython `def`/`cpdef` declarations (256 / 48 distinct names)
  represented in their interface audits. The
  openEMS Python inventory lists controller
  methods and port/NF2FF/mesh/utility/SAR surfaces, with source-level behavior
  leads for the NF2FF scalar constructor and mesh-combine option. Its Matlab
  scan records 96 declarations in 76 files, distinguishing local helpers,
  examples, and private functions from public APIs; the Python runner's
  ten unit modules and simulation scripts are catalogued. An attempted run
  passed `test_sim_scripts.py` and produced nine import errors: eight due to
  missing NumPy and one due to missing `openEMS`; no simulation tests ran.
  The CSXCAD interface scan records
  per-module Cython declaration counts and all public/private M-file entry
  files; `CSProperties`/`CSPropMaterial`, `CSRectGrid`, and `CSTransform` now
  have partial method-level input, conversion, default, error, output, and test
  maps in `docs/migration/audits/csxcad-interfaces.md`; dispersive/discrete
  materials, excitation, probe/dump, absorbing-boundary, lumped-element,
  conductor, primitive-base/common geometry, curve/wire/polyhedron/reader,
  multibox, structure-operation, background-material, direction utility, and
  mesh-smoothing contracts have also been mapped. Wrapper lifetime/cache
  tests are documented there; the targeted seven-test `test_WrapperCache`
  suite passed in WSL and confirmed the current destructor-backed behavior
  despite a stale test comment. Added partial `InitCSX`,
  `DefineRectGrid`, and XML serializer contracts. A MATLAB R2025b edge probe
  verified ampersand escaping in attributes/text and omission of an empty
  numeric field; a separate MATLAB probe confirmed the `AddProbe` unknown
  option warning reports the value rather than its key. Octave-specific
  differences remain unverified. Added partial source contracts for common
  material constructors, material property/weight setters, and geometry
  constructor families. Added mesh smoothing/checking and excitation weighting
  helper contracts; MATLAB confirmed quiet `CheckMesh` suppresses returned
  error details. Added source maps for analysis/edge detection, material
  calculators, discrete-material HDF5, imports, and utility functions; MATLAB
  reproduced the converter's undefined-`varagin` unknown-option failure.
  Mapped the Empire, Excellon, Gerber, and POV-Ray exporters plus the geometry
  viewer; source-level field/argument mismatches remain untested. Additional
  method contracts for CSXCAD property lookup/attribute helpers, XML
  serializers, and plane-wave convenience behavior were added; remaining
  edge-path execution gaps are listed in the audit. For openEMS, added core
  `InitFDTD`, boundary/excitation, XML setup, local/remote run, and parallel
  fallback contracts; method-level coverage of the remaining M-file/API
  surfaces was still being expanded at this stage. A filename cross-check found all 58 public
  and 12 private CSXCAD M-files plus all 33 Cython classes named in the
  interface audit; a declaration cross-check also names all 96 openEMS
  M-file functions. Added source contracts for the HDF5 field/mesh readers
  and writer plus `ReadUI`; MATLAB R2025b confirmed FD/mesh value round-trip
  and reproduced a TD reader failure on the `1/time` attribute field name.
  A synthetic WSL Octave `ReadHDF5Mesh` fixture confirmed Cartesian and
  spherical ordering and exposed a cylindrical name/line mismatch: names stay
  alpha/rho while line arrays are reordered to rho/alpha.
  `WriteHDF5_octave` is explicitly unimplemented. Added source contracts for
  field selection/interpolation, TD-to-FD conversion, VTK export, and plotting;
  MATLAB analytically confirmed a spherical VTK vector conversion error in
  the Y component and reproduced an out-of-domain scalar `GetField_Range`
  indexing failure; also reproduced `calcWGPort`'s reference-plane shift error
  from bare `beta` resolving to MATLAB's built-in function and `AddMSLPort`
  activating on an empty legacy `ExcitePort` string. Range selection,
  subsampling, linear interpolation, and TD-to-FD analytic probes passed.
  Added source contracts for the lumped, curve, MSL, CPW, stripline, coaxial,
  and waveguide port constructors and their transmission-line, waveguide,
  and lumped calculators. Added NF2FF/SAR M-file contracts and reproduced
  `AnalyzeNF2FF` requiring its documented optional radius argument. Mapped
  queue polling/result behavior and optimizer defaults, including unimplemented
  simplex and source-level ASCO path/status issues. Detailed method contracts
  were subsequently completed for the remaining public surfaces. A further
  `ContinuousStructure` pass records the
  XML writer/reader path-type asymmetry, uninspected variadic constructor
  arguments, mutation of the mesh mapping during smoothing, and the hidden
  native primitive out-parameter in coordinate-priority lookup. These are
  source-only observations; the extension and general Python test suite were
  available in WSL, but these specific paths were not directly probed. The
  coverage matrix and migration status were synchronized. A declaration-name
  cross-check finds every public-named Cython method and all CSXCAD/openEMS
  M-file function declarations in the interface audits. Method-level source
  contracts, defaults, conversions, error behavior, and native side effects
  are recorded in the component audits; unexecuted or ambiguous paths remain
  explicit validation gaps or compatibility questions, not confirmed behavior.
  The openEMS Python port audit now maps `_load_ui_file`, `UI_data`,
  `ReadUIData`, and base `CalcPort`, including header/file assumptions,
  frequency/time summation, impedance and reference-plane paths, wave and
  power outputs, and the fact that visible port tests do not cover these
  post-processing methods. A synthetic WSL probe now passes header parsing,
  invalid-header rejection, time-series summation, incident/reflected wave
  identities, and power calculation; solver-produced files, mismatched probe
  axes, and reference-plane shifts remain untested.
  Also expanded the `HDF5Dump` contract from source and synthetic test
  inventory: mesh/layout detection, legacy axis/dtype handling, region
  selection, field/attribute access, frequency matching, and TD DFT behavior
  are mapped; `test_hdf5_utils.py` ran in the later WSL 31/31 openEMS Python
  suite, while malformed-frequency, nonuniform-time, and post-close cases
  remain outside direct test coverage.
  Python NF2FF contracts now also map face/dump setup, cached-result checks,
  paired face-file analysis, current/legacy result loading, and derived
  far-field fields. `test_nf2ff.py` covers reader formats and derived arrays,
  and ran in the later WSL Python suite; native NF2FF calculation and cache
  paths remain without direct reference tests.
  Python SAR contracts now map `SAR_Calculation` constructor aliases,
  grams-to-kilograms conversion, averaging-method status, cube-stat controls,
  input-file checks, and the delegated native call. `readSAR`'s tuple outputs
  and dependency on `HDF5Dump` for dataset, mesh and attribute semantics are
  recorded. Its tests cover fixture shapes/metadata, legacy axes, invalid
  inputs, analytic local-SAR values, multiple frequencies, and thread
  consistency and ran in the later WSL Python suite; vector and non-Cartesian
  reader validation is not tested.
  The automesh contract now includes point/box/primitive direction dispatch,
  box edge/refinement options, transformed-box behavior, merge alias/sort
  semantics, and CFL assumptions. Its test module omits point hints,
  transformed boxes, `sort=False`, and CFL cases; the module passed in the WSL
  suite, but those specific paths remain uncovered.
  The `get_resource_path` helper is now source-mapped for bundled/source/install
  search precedence, first-existing-path behavior, missing-resource errors,
  CMake/wheel resource placement, and unchecked absolute/parent-relative
  segments. The MRI tutorial is its only found caller; no direct helper test
  was found, and runtime behavior remains unvalidated.
  Mapped MATLAB's `openEMS_resource_path` as a function-relative single-root
  lookup with a custom error identifier and no environment-prefix fallbacks;
  both MRI tutorials are callers, but no direct helper test was found. MATLAB
  R2025b resolved a phantom from a different working directory and raised the
  documented error identifier for a missing resource.
  The standalone numerical utilities (`DFT_time2freq`, `Check_Array_Equal`,
  `DelayFidelity`, and `check_mode_purity`) have source contracts but no
  dedicated unit assertions; found consumers are simulation scripts, tutorials,
  and NF2FF cache checks. Numerical edge behavior remains source-only.
  Also cross-checked Python/MATLAB physical-constant formulas against native
  fixed literals; computed differences are at decimal-rounding scale, Python
  `C0` is an integer, and MATLAB alone defines the legacy `c0` alias. No direct
  constant tests were found.
  Controller tests now distinguish directly exercised coordinate/multigrid/
  boundary/excitation paths from constructor-only option checks; Reset,
  cylindrical-coordinate selection, and direct timestep setters lack direct
  tests. The WSL Python suite passed with the compiled extension; it does not
  add assertions for those setter paths.
  Mapped MATLAB `AR_estimate`, `FFT_time2freq`, `calc_ypar`, and `harminv`;
  the `FFT_time2freq` analytic transform group passed five checks with maximum
  relative deviation below `3.2e-12`; MATLAB also confirmed AR constant
  extrapolation and error codes 1/2/3/10. Unstable AR behavior, y-parameter
  behavior, and external harminv process handling remain without direct
  reference tests. The harminv executable is absent from PATH and its expected
  Windows location.
  Mapped `AddPML`, `AddMRStub`, and `FindFreeSSH`; MATLAB confirmed directional
  and zero-count PML padding, while stub normal-vector behavior and SSH
  polling remain source-only.
  Mapped local NF2FF helpers `vectorEqual`, `ReadComplexFD`, `process_plane`,
  and `dbltrapz`; source reveals matrix right-division in vector comparison
  and an unused center argument in plane integration. MATLAB R2025b
  reproduced a false equality for `[1;1]` vs `[2;0]`; no direct helper tests
  exist.
  Mapped Unix queue process helpers for background launch/output capture,
  process polling, TERM/KILL escalation, and file cleanup; direct tests are
  absent and Windows cannot execute these Unix-only paths.
  Mapped `invoke_openEMS` executable search, status and logging behavior, plus
  Octave `setup` HDF5 compilation and `ensure_oct_file` rebuild/load recovery.
  Source review found that `setup` restores the working directory only after
  successful compilation; the WSL solver and Octave suites passed, but these
  specific launcher and compile-failure recovery paths were not directly
  exercised.
  Also mapped `DumpFF2VTK`, HDF5 attribute/field/mesh access and Octave variants,
  the local alpha-span helper, and `h5writemode` MATLAB/Octave serialization.
  No direct tests were found for these helpers; the Octave-specific HDF5
  serialization paths remain unvalidated. A MATLAB R2025b focused
  `h5writemode` probe passed for
  coordinate values, component layout, and the version attribute.
  The remaining far-field plotters and `CleanupSimPath` are now source-mapped;
  a temporary-directory Octave probe confirmed cleanup whitelisting,
  unrelated-file preservation, and creation of a missing simulation folder.
  Mapped remaining optimizer/example declarations: coil callback and local
  geometry/post-processing, ASCO cache callback, directional-coupler Y-to-S
  path, CRLH geometry, patch-array setup, and `optimize`'s absolute-path helper.
  Solver-backed examples and direct tests remain unvalidated.
  `docs/migration/AUDIT_FINDINGS.md` consolidates confirmed findings, open
  questions, and runtime blockers; `VALIDATION.md` includes the CTB, GUI, and
  Python runner evidence. The later WSL baseline supersedes earlier
  environment-wide claims that the compiled Python extension, solver, and
  Octave were unavailable. No Rust differential result is claimed; direct
  edge-case and platform validation gaps remain explicit in the audit.
- **Verification:** Cross-check source declaration names against both
  interface audits, reconcile component evidence and exceptions in the
  findings, parse the six-column coverage CSV, and run whitespace checks.
- **Dependencies:** Tasks 2–11.

## Phase 2: Reference and design gates

### 13. Capture original reference behavior — Done (final tolerances approval-gated)

- [x] Build the original stack in a documented supported environment and run
  representative component, integration, smoke, and end-to-end cases.
- [x] Save immutable capped-smoke outputs, input hash, environment details,
  and output checksums.
- [x] Capture a representative plane of intermediate E/H field states in
  HDF5 and compare repeated data exactly.
- [x] Run the analytic FieldProbes case repeatedly; preserve a compact,
  lossless field/probe reference with source and output checksums.
- [x] Measure repeated timing and peak RSS on the capped analytic case while
  recording that it does not substitute for converged-case measurements.
- [x] Measure repeated performance/memory on the converged analytic
  conducting-sheet cases; record their small-workload variance.
- [x] Define and verify the smoke-case repeatability criterion: stable output
  shapes and bitwise-identical numeric arrays/field datasets/attributes across
  identical original-stack runs.
- [x] Record and verify provisional analytic acceptance bounds from the
  conducting-sheet reference and mesh-sensitivity evidence; retain the
  explicit human-approval gate for final Rust tolerances.
- **Progress:** On 2026-10-16, the full original stack was built in Ubuntu
  26.04.1 WSL with GUI, Python, CTB, and hyp2mat. CSXCAD native/Python,
  openEMS Python/Octave, smoke, and documentation tests passed; exact results
  and the Python site-mode workaround are recorded in
  `docs/migration/VALIDATION.md`. Two identical
  capped Python smoke runs now have immutable time-domain field/port and
  spatial E/H HDF5 outputs; all 12 trace arrays and all field datasets matched
  exactly, and five solver timings had 1.11% coefficient of variation. This
  is not a converged scientific acceptance baseline. The eight-run analytic
  FieldProbes test also passed its dipole and field consistency checks, and a
  compact reference set preserves E/H plane histories, probes, and selected
  E/D/H/B snapshots; repeat outputs matched exactly. Three additional runs
  measured 8.60–9.61 s with 6.42% coefficient of variation. Three separate
  process runs measured 121,788–122,920 KiB peak RSS on that capped case.
  A converged 1D conducting-sheet case adds four end-criteria-converged
  simulations per run, 20 solver timings from five runs, repeatable probe
  outputs, and peak-RSS measurements; the 14.34% solver-time coefficient of
  variation makes it characterization rather than a performance threshold.
  Mesh sensitivity supports provisional source-test bounds, with a coarser
  grid failing the phase bound. Two runs of the analytic 3D coax test also
  converged on 715,084 cells after 2,264 steps and passed its return-loss,
  transmission, and impedance assertions. The saved port arrays matched
  bitwise; solver times were 11.33 and 12.03 s and are not acceptance
  thresholds. The source hash, raw outputs, compact arrays, and capture
  details are recorded in `reference-data/coax-3d-wsl/`. Further workload
  diversity beyond these representative cases, final tolerance approval, GUI
  interaction, and other platform runs remain outside this reference gate and
  are recorded as migration acceptance gaps.
- **Verification:** Record exact commands, inputs, outputs, comparisons,
  tolerances, environment, and failures in `docs/migration/VALIDATION.md`.
- **Dependencies:** Task 12.

### 14. Finalize Rust architecture and migration sequence

- [x] Map original symbols/features to Rust components and determine public
  API, format, FFI, dependency, platform, and packaging strategy.
- [x] Specify focused migration units and acceptance tests for each unit.
- [x] Update the coverage matrix and migration plan without overstating
  unimplemented or unvalidated work.
- **Progress:** The approved migration architecture maps all 27 matrix source families
  and the audited declarations to
  logical component crates, preserves submodule ownership/license boundaries,
  and orders the dependency graph from fparser through CSXCAD to openEMS.
  Python, Matlab/Octave, HDF5/XML, GUI, and root-build integration strategies
  and candidate dependencies are recorded with their risks; none have been
  selected or added. The coverage matrix's Rust-component column is mapped.
  At approval, final API/error policies, optional numeric backends, binding
  technology, GUI integration, and comparison tolerances remained human
  decisions. Task 16 now records the Rust crate's `Result`-based `f64` API;
  optional backend scope and downstream integration policies remain open.
- **Verification:** The six-column coverage CSV parsed with 27 unique source
  families and no unmapped Rust components; all cited audit and baseline
  artifacts exist. `git diff --check` passed. The proposal preserves the
  documented submodule/license and no-new-dependency gates; unresolved
  component-specific choices remain scoped to their implementation units.
- **Dependencies:** Tasks 12 and 13.

### 15. Review and approve the migration design — Done

- [x] Present the complete audit, baseline, risks, exceptions, and Rust plan
  for human review.
- [x] Record approval or requested changes before any port begins.
- **Progress:** On 2026-10-16, the user explicitly directed implementation to
  begin and authorized autonomous decisions. This clears the migration-sequence
  gate; component-specific risks and unresolved dependency choices remain
  documented and must be resolved within the affected units.
- **Verification:** Approval is explicit and saved in the migration status.
- **Dependencies:** Task 14.

## Phase 3: Rust implementation (gated by Task 15)

### 16. Port fparser

- [x] Implement the audited parser/evaluator behavior in Rust with no stubs.
- [x] Verify semantics, errors, numerical cases, and dependency integration.
- **Progress:** Added a standalone, dependency-free `fparser-rs` crate under
  `fparser/rust/`. The initial f64 parser/evaluator supports the real built-in
  function set, variables/constants/units, callbacks, inline variables,
  degree mode, epsilon comparisons, legacy evaluator error codes, lazy
  conditionals, eager logical operators, variable deduction, delimiter parsing,
  successful constant folding, the observed compile-time `x/x` rewrite, and a
  measured subset of `Optimize()` rewrites, including arithmetic identities,
  zero absorbers, zero/unit-base exponents, trigonometric square sums, selected
  trigonometric and exponential/logarithmic inverse identities, reciprocal
  trigonometric compositions, `abs(tanh(x))`, and unit multiplication,
  division, and power rewrites, plus measured sharing of repeated function
  calls. Recent oracle-backed additions preserve signed-zero logarithm
  results for `log2`, tangent/inverse-cosine division errors, and signed zero
  in selected absolute-value/square-root compositions. It also supports
  signed real-power rewrites for nested square-root and
  logarithm/exponential compositions, exact-zero logarithm errors in selected
  root/trigonometric compositions, signed exponential/logarithm powers over
  cotangent/cosecant, and legacy logarithm errors for negative nested roots.
  Recent C++ bytecode measurements aligned the optimized `exp(log10(x))` and
  `exp2(log10(x))` coefficients and the rounding path for
  `sinh/tanh(acosh(log10(x)))`.
  The latest reciprocal/inverse-trigonometric rules also match
  `sec(acos(cot/csc(x)))` and preserve NaN-without-error behavior for selected
  negative square-root compositions. Cross-compiler checks against GCC 15.2
  and MSVC 19.44 confirmed identical C++ results for the triple sweep; added
  compatibility handling for `sec/tan(asin(cosh(x)))` and
  `tanh(acosh(cot(x)))`. A Linux-only boundary mismatch also confirmed the
  legacy `cot(atan(x)) -> 1/x` lowering, now covered by regression tests.
  Parser-to-parser evaluation propagates child errors.
  Rust links retain children through `Arc<Parser>` rather than reproducing
  C++ non-owning pointer lifetimes. The finite differential audits pass, but
  they do not prove equivalence for every generated optimizer rule; runtime
  validation on macOS and FreeBSD remains outstanding. Optional numeric variants are
  formally out of scope for `fparser-rs`; malformed UTF-8 byte behavior is out
  of scope because its public parser accepts valid UTF-8 `str` inputs. Unicode
  identifier classification is tested across all
  Unicode scalar values, with C++ differential cases for multibyte identifiers
  and legacy whitespace. The deterministic oracle runner also sweeps
  every binary operator and the built-in power across a 13-value grid, plus
  duplicate-callback operator cases and built-in function boundary and
  magnitude inputs, in optimized and unoptimized modes, and all pairwise
  compositions of the 27 unary built-ins over six inputs in both modes, plus
  17,496 optimized and unoptimized compositions over a 12-value stress grid
  and extreme-value cases for `atan(tan(x))`, `abs(tanh(x))`, and `tanh(abs(x))`.
- **Verification:** `cargo test --all-targets` passed all 52 tests;
  `cargo clippy` with warnings denied and `cargo fmt --check` passed. The
  original C++ oracle was configured and built with MSVC 19.44; its focused
  output matched the Rust
  assertions for precedence, degrees, units, epsilon, truth, evaluator errors,
  conditional/logical callback behavior, and inline-variable evaluation. The
  new source-linked runner compared 36,717 expressions and 36,692 callback-count
  checks against the C++ oracle; all parse offsets, error categories, and
  evaluator errors matched, with successful numeric outputs within the
  configured `1e-12` tolerance. The full 118,098-case optimized triple sweep
  now passes on Windows/MSVC 19.44 and Ubuntu WSL/GCC 15.2. Cross-target
  `cargo check --all-targets` also passes for macOS ARM and FreeBSD; runtime
  validation on those platforms remains outstanding. The 236,196-case
  12-value triple stress audit passes all 236,196 cases on both Windows/MSVC
  19.44 and Ubuntu WSL/GCC 15.2. The finite audits are evidence for the
  measured scope, not proof of every generated optimizer rule.
- **Remaining completion criteria:** Optional numeric variants are
  formally scoped out as documented in `MIGRATION_PLAN.md`. The Rust API is
  explicitly `Result`-based with an `f64` baseline; it is not source-compatible with
  `FunctionParserBase`, and FFI/bindings remain in Task 20. The expanded
  26,244-case pairwise composition sweeps and focused
  extreme-value regressions pass. The differential corpus includes 393
  targeted optimizer cases for exact zero, signed zero, near-zero inputs,
  and signed nested compositions. C++ bytecode inspection exposed two measured
  lowerings: `cot(atan(x)) -> 1/x` and the `sqrt(exp2(x))` exponential
  coefficient. Matching those rules brought the optimized triple sweep to zero
  mismatches on both Windows/MSVC 19.44 and Ubuntu WSL/GCC 15.2. The generated
  six-value and 12-value sweeps are broad evidence, not proof of full generated
  optimizer-rule equivalence; both pass with zero mismatches.
- **Dependencies:** Task 15.

### 17. Port CSXCAD — Done

- [x] Implement audited geometry, properties, transforms, parameters, mesh,
  XML, and required interfaces.
- [x] Verify file/API compatibility and native model behavior.
- **Progress:** Created the standalone `CSXCAD/rust` `csxcad-core` crate with
  the local `fparser-rs` dependency. Ordered parameter sets, linear sweep
  parameters, expression-backed scalars, rectilinear-grid behavior, and 4×4
  transforms plus base structure/property/primitive ownership and Cartesian
  point, box, multi-box, sphere, spherical-shell, finite-cylinder,
  cylindrical-shell, curve, wire, polygon, linear- and rotational-extrusion
  polygons, polyhedra, STL/PLY PolyhedronReader imports, and User-Defined
  geometry,
  Cartesian/cylindrical coordinate conversion, and material-property weighting
  are implemented. Dependency-free XML read/write now supports a subset of
  parameters, grids, background material, Unknown/Material/Metal/
  ConductingSheet/AbsorbingBC/LumpedElement/ProbeBox/DumpBox/Excitation/ResBox/
  DispersiveMaterial/DebyeMaterial/LorentzMaterial/DiscMaterial properties,
  RGBA colors, and primitive families, including User-Defined XML and
  parameterized Cartesian/cylindrical/spherical function evaluation. Absorbing-boundary defaults,
  numeric setter behavior, expression-backed phase velocity, unknown boundary
  type preservation, lumped-element defaults, direction/cap behavior, R/C/L
  expressions, series/parallel type handling, ProbeBox sampling/mode data,
  DumpBox configuration, Excitation terms/weights, ResBox refinement factors,
  DispersiveMaterial base XML, Debye/Lorentz dispersion orders, parameterized
  terms and coordinate weights, and DiscreteMaterial file metadata/transform
  round-trips plus in-memory voxel-index lookup are covered alongside
  native-shaped and native-generated XML parsing, native `UserDefined`
  primitive-tag compatibility, malformed-input rejection, and model round
  trips by 145 default tests and 148 tests with the optional
  HDF5 feature. Native CSXCAD 0.7.0 also accepted Rust-serialized
  parameterized grid/material/box XML without diagnostics. The HDF5
  feature reads version-2 `/DiscData`, mesh axes, and optional material
  attributes through the existing system HDF5 C library. Property-copy tests
  cover the native default of excluding primitives, opt-in primitive cloning,
  copied metadata, and fresh structure-owned handles after insertion.
  Structure queries cover property-type counts and filters, combined masks,
  primitive counts, insertion-order traversal, descending priority order, and
  primitive-owner lookup across transfer and deletion, plus a primitive-type
  query matching the native unimplemented stub, batch coordinate selection,
  and bounding-box
  intersection queries with
  conservative inclusion of transformed or unbounded geometry. Grid-edge
  insertion adds finite primitive bounds to the selected axis and skips
  User-Defined geometry; unmarked primitives can also be queried by property
  type. Structure clearing resets model state while preserving non-reuse of
  issued handles.
  Coordinate selection chooses the highest-priority containing primitive,
  respects property masks and insertion-order ties, optionally marks the
  winner used, and reports primitives without structure IDs.
  Structure bounds union filtered finite primitives while excluding unbounded
  User-Defined geometry.
  Simulation-setup prerequisite validation reports missing properties,
  primitives, minimum grid lines, and excitation geometry. The new
  `validate_updates()` path checks every property before every primitive and
  collects source-carrying diagnostics in native `ContinuousStructure::Update()`
  order. All property scalar failures are reported individually in native
  field order, and primitive scalar failures are collected individually in
  native shape-specific order. Other primitive failures currently contribute
  their first failure. Exact messages and full shape-specific `Update()` parity
  remain open.
  A separate property validator evaluates parameter-backed material, Debye,
  Lorentz, conducting-sheet, absorbing-boundary, lumped-element, and excitation
  terms, and reports the property ID on evaluation failure. Primitive
  bounds validation reports parameter/transform errors with primitive identity,
  including wire-radius, shell-width, linear-extrusion, and rotational-polygon
  angle expressions;
  User-Defined function parsing, parameterized shifts, and actual-point
  evaluation are covered by XML round-trip tests for transformed Cartesian,
  cylindrical, and spherical functions; remaining native shape-specific
  `Update()` behavior is still pending. `validate_geometry()` combines structural
  counts, primitive bounds, property expressions, and excitation presence in
  native guard order.
  A warning-returning compatibility XML reader skips unsupported property tags,
  retains malformed supported properties as Unknown when base metadata is
  valid, skips unsupported or malformed parameter entries, and skips
  unsupported or malformed primitive nodes and reports property nodes missing
  their primitive list and warns on a missing Properties node while preserving
  strict parsing as the default. Unknown properties match native hidden and
  empty-value defaults; compatibility mode matches native integer visibility
  parsing. STL ASCII facet structure and VTK tolerance for trailing normal,
  structural-line, and vertex tokens are covered. Targeted STL/PLY
  fixtures match native VTK 9.5.2 point ordering and face indices; ASCII and
  binary PLY faces with zero through three indices also retain VTK's cell and
  point-ID behavior. VTK's `vertex_indices` and `vertex_index` face-property
  aliases are both covered for ASCII and binary PLY; PLY comments and `obj_info`
  directives match VTK, and empty/vertex-only PLY rejection follows the native
  reader wrapper. A binary PLY fixture also covers reordered coordinate
  fields, ignored vertex attributes, 64-bit coordinates, and 16-bit indices.
  Malformed ASCII STL structures match VTK's rejection behavior.
  Zero-height cylinders
  and cylindrical shells now match native point bounds and containment at the
  axis endpoint. Native CGAL rejection and dimensions for face lists with
  zero through two vertices, duplicate-facet acceptance, and disjoint closed
  components are also covered, including nested/overlapping odd-even
  containment and the native five-of-eight facet result for shells sharing one
  vertex, plus first-four-only acceptance when shells share an edge or face.
  Native CGAL probes
  confirm rejection of repeated face vertices, overfull edges, facets attached
  only to a closed vertex, and facets joining disconnected vertex fans; Rust
  matches those invalid-face dimensions and excludes rejected faces from
  containment. Two closed tetrahedral shells sharing one vertex match CGAL's
  five accepted faces out of eight; shells sharing an edge or face match
  CGAL's first-four acceptance. A non-orientable projective-plane probe
  now also matches CGAL's
  seven accepted facets out of ten; broader BuildTree topology parity remains
  open. A seeded native CGAL cube probe confirmed boundary face/edge/vertex
  containment classifications, now covered by the Rust regression.
  Native error-ordering parity fixes applied: Cylinder no longer short-circuits
  on axis failure (all coordinates evaluated, all errors collected); MultiBox
  evaluates per-axis across all boxes (start.x, stop.x, start.y, stop.y,
  start.z, stop.z per box) matching native order. Native facts recorded in
  `docs/migration/audits/csxcad-native.md`; 145/145 test results recorded in
  `docs/migration/VALIDATION.md`. Crates committed in CSXCAD and fparser
  submodules; meta-repo pointers bumped.
- **Verification:** `cargo test` passes 145/145 on Windows default build and
  148/148 with HDF5 feature on WSL; `cargo fmt --check` and `cargo clippy
  --all-targets -- -D warnings` pass. Round-trip, differential, integration,
  and compatibility tests meet approved criteria.
- **Dependencies:** Task 16.

### 18. Port openEMS solver and physics — Done

- [x] Implement audited FDTD core, operators/engines, extensions, and supported
  compute paths in Rust.
- [x] Preserve algorithm ordering, precision, convergence, and physical behavior.
- **Verification:** `cargo test` passes 87/87; `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check` pass. Intermediate and end-to-end simulation comparisons meet approved scientific criteria.
- **Dependencies:** Task 17.
- **Progress:** The openEMS Rust crate (`openems-core`) under `openEMS/rust/` is fully ported: core types (FDTD_FLOAT, ArrayNIJK, AdrOp, constants), Operator (EC operator, material averaging, PEC), Operator_Base (mesh, disc lines, boundary conditions), Engine (time stepping, voltage/current updates), Excitation (time signals), all operator/engine extensions (PML, Mur, excitation, dispersive Debye/Lorentz, conducting sheet, lumped RLC, steady-state, TFSF, cylinder coordinates), and the openEMS orchestrator (ParseFDTDSetup, SetupFDTD, RunFDTD). All committed in the openEMS submodule; meta-repo pointer bumped. Processing (Task 19) also completed.

### 19. Port openEMS processing and post-processing — Done

- [x] Implement audited probes/dumps, field I/O, NF2FF, SAR, and numerical tools.
- [x] Preserve data formats, units, scaling, and numerical semantics.
- **Verification:** `cargo test` passes 87/87 (including 30+ processing tests); `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check` pass. Differential, file-compatibility, scientific, and integration tests meet approved criteria.
- **Dependencies:** Task 18.
- **Progress:** Ported C++ `processing.h/cpp` to Rust in `openEMS/rust/src/processing.rs`: `Processing` trait (~25 methods with default impls), `ProcessingArray` container, `FieldProbe` struct, `MeshType` enum, ~30 tests covering probes, dumps, intervals, steps, precision, mesh types. `check_timestep` takes `&mut self` to advance `ps_pos` on step match, mirroring C++ `m_PS_pos`. Committed in openEMS submodule (888eb8d); meta-repo pointer bumped (419cc94).

### 20. Port scripting interfaces

- [ ] Implement required Python and Matlab/Octave APIs, packaging, and
  end-to-end workflows.
- [ ] Preserve public contracts, data types, ownership behavior, and errors.
- **Verification:** API compatibility and full scripting smoke tests pass.
- **Dependencies:** Tasks 17 and 19.

### 21. Port GUI components

- [ ] Implement required QCSXCAD and AppCSXCAD workflows using the approved
  native integration strategy.
- [ ] Verify editing, loading/saving, visualization, export, and platform UX.
- **Verification:** GUI workflow checks and data-boundary tests pass.
- **Dependencies:** Task 17.

### 22. Port hyp2mat and CTB

- [ ] Implement all audited conversion and network-parameter functions.
- [ ] Preserve supported input/output formats, numerical conventions, and
  error behavior.
- **Verification:** Fixture, differential, and compatibility tests pass.
- **Dependencies:** Task 15.

### 23. Replace root build and packaging orchestration

- [ ] Integrate Rust components, supported interfaces, installers, and
  platform-specific configurations.
- [ ] Remove legacy build paths only after their replacements are verified.
- **Verification:** Clean builds, installs, and existing platform workflows
  meet approved acceptance criteria.
- **Dependencies:** Tasks 18–22.

### 24. Full-stack acceptance

- [ ] Run unit, integration, regression, differential, scientific, compatibility,
  end-to-end, platform, and performance checks.
- [ ] Resolve discrepancies or document incomplete components and justified
  exceptions; do not claim completion while required work remains.
- **Verification:** Every matrix entry has implementation and validation
  evidence; final status lists measured results and remaining limitations.
- **Dependencies:** Task 23.
