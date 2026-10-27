# Rust Migration Status

**Status (2026-10-25):** The canonical tree is
`mberkanbicer-rust-migration-audit` in this worktree. All seven submodule ports
are committed on their own `mberkanbicer-rust-migration-audit` branches, pushed,
and pinned by the root repository; the archived three-crate tree is tagged
`archive/rust-3crate-tree-2026-10`. The numerical core builds and its 375 tests
pass, including analytic propagation, UPML absorption, CFL, quarter-cell
material averaging and native-HDF5 dump reading.

Remaining work is tracked per task in `docs/migration/REMEDIATION_TASKS.md`
(80 `Verified`, 55 `Implemented`, 10 `Not Started`, 3 `Blocked` at the last
update; see the snapshot there for the live count). The largest open areas are the extension
framework and remaining physics extensions, NF2FF/SAR, the native CLI and
scripting interfaces, the GUI feature surface, and the differential harness over
`reference-data/`.

### Status and evidence policy

`Not Started` -> `Analyzed` -> `Implemented` -> `Integrated` -> `Verified`, plus
`Blocked`. `Verified` requires an executed comparison recorded in
`VALIDATION.md` with an approved tolerance; a build is not a verification. The
authoritative counts and evidence are in `REMEDIATION_TASKS.md`. See Section 0 of
`REMEDIATION_PLAN.md` and `EXCEPTIONS.md`.


## Baseline

- Root repository: `mberkanbicer/openEMS-Project`, commit
  `974294b` (`release: v0.37.0`).
- All seven submodules are initialized at their pinned revisions:

  | Component | Revision |
  | --- | --- |
  | AppCSXCAD | `f04d3a7d7cce31c57704f14abe46c66684c15c7d` |
  | CSXCAD | `c46e3206f20027b0b4605c797d07bddab76de942` |
  | CTB | `934c76543a5811e49b93bb7f6cc841a0d3931b9f` |
  | QCSXCAD | `26d7ee13440cff0e5621a6b9d325ae31d118bc2d` |
  | fparser | `4b9c845b449b520c4b8c5f23c74cd04820084f81` |
  | hyp2mat | `b15f749849610066e6c09da5b5e3f97e3317ba8a` |
  | openEMS | `305df56aa7df4d2f18c687083f484a96f9a22610` |

The original stack was built in Ubuntu 26.04.1 under WSL on 2026-10-16 with
GCC 15.2.0, CMake 4.2.3, Python 3.14.4, and Octave 11.1.0. The root build
passed with GUI, Python, and CTB enabled; a second root build passed with
`--with-hyp2mat`. The initial offline `site` venv mode failed because
`scripts/build_python.sh` passes the wrong array name; using a manually
created system-site venv with Python venv mode disabled let the build pass
without source changes. CSXCAD C++ tests passed 2/2, CSXCAD Python tests
passed 150 (one skipped), the openEMS Python suite passed 31/31, the Octave
suite passed 10/10, both MSL smoke tests passed, and the Sphinx build completed
with zero warnings. Two capped smoke field/port traces and repeated E/H HDF5
plane snapshots are preserved under `reference-data/msl-notchfilter-wsl/`;
their numeric data matched exactly. Five smoke solver-time observations had
1.11% coefficient of variation, but the capped case is not a converged
physical or performance acceptance baseline. Broader intermediate-state
coverage, GUI interaction, and cross-platform builds remain open. The
FieldProbes analytic dipole case has a compact field/probe reference and
repeatability data, but stops before its end criterion. A separate converged
conducting-sheet test now provides analytical transmission data, repeated
timing/memory measurements, and provisional acceptance bounds; its small 1D
workload is not a general solver performance threshold.
A converged 3D coaxial-line reference now adds analytic port and impedance
checks on a 715,084-cell mesh; two runs matched all saved numeric port arrays
bitwise. Its solver timings are characterization only.

## Wave C status (2026-10-26)

The scripting wave is verified for the Python **and** the Octave/MATLAB
interfaces.

Python: the unmodified native CSXCAD suite (150 tests) and the unmodified native
openEMS Python suite (298 tests) pass against the Rust core
(`scripts/ci/run_rust_python_tests_wsl.sh`), including the controller, every port
class, XML round-trips, NF2FF results, SAR and the HDF5 readers.

Octave/MATLAB: the unmodified native testsuite runs through the Rust binaries
(`scripts/ci/run_octave_testsuite_wsl.sh`):

```
PASS unittests/port_setup, unittests/transforms, probes/fieldprobes,
     combinedtests/Coax, combinedtests/cavity, combinedtests/msl_port,
     combinedtests/nf2ff_dipole, combinedtests/rect_waveguide,
     enginetests/engine_compare
PASS combinedtests/coax_cylindrical    (RM-134, cylindrical operator)
10 passed, 0 failed, 0 errors in 334 s
```

`combinedtests/Coax` now reports Z = 50.09..51.12 Ohm against the native
reference 50.49..51.10 Ohm and the analytic 49.94 Ohm. The MSL smoke tests
(`.github/smoketests/{octave,python}/MSL_NotchFilter`) complete unchanged.

What made the interface work, in order of impact:

1. `setup_fdtd` now applies the `<Excitation>` and `<BoundaryCond>` children of
   `<FDTD>`; previously only the Python controller supplied them, so a plain
   `openEMS file.xml` run excited a default 1 GHz/500 MHz pulse and had no PML
   (the domain rang as a lossless cavity).
2. The default timestep method is the native Rennings_2 (3), restoring the
   native 9.629 ps step on the Coax mesh.
3. The excitation weight function is evaluated at the Yee vertex in metres
   (`GetWeightedExcitation`), fixing the TEM port amplitude.
4. Probe and dump snapping use the native `SnapToMeshLine` floor rule, field
   probes return physical E/H (`GetRawField`), and processed samples are written
   with the native `setprecision(12)` general format (the previous fixed-point
   time column quantised 1.44e-10 s to 1 ps and corrupted the Octave FFT).
5. CSX `DumpBox` properties drive real time-domain dumps (cropped, physical
   units, native `DumpMode` 0/1/2 interpolation, dual mesh/time for H/B,
   `NXYZ` or legacy `NZYX` layout), which is what `probes/fieldprobes` and the
   NF2FF box faces need.
6. New Rust binaries `nf2ff` (native `<nf2ff>` XML contract) and `sar_calc`
   (native option set) are linked under the native names.

The cylindrical operator closed the last deferred case (RM-134): the native
`(rho, alpha, z)` metric, the closed-azimuth seam and the `1/rho` excitation
weight are ported, and `combinedtests/coax_cylindrical` passes (beta = k0
within 0.20 %, radial profile within 0.013 %, symmetry 7.6e-17).

Direct SAR result dumps (`DumpType` 20..22) are verified as well (RM-136):
the in-solver `SAR_Calculation` writes local and 1 g results, and the test
script compares them against the raw dump + `sar_calc` path (peak 6.5e-9
relative, homogeneous interior bit-identical).

Known gaps tracked separately: cylindrical multi-grid
(`Engine_Ext_CylinderMultiGrid`, radii stored but the hierarchy is not ported),
the SAR 1 g/10 g averaging-cube search (RM-145), the end-criteria stop time
(RM-146) and cylindrical port/line snapping plus `--nativeFieldDumps`
(RM-144, blocked on the wire-excitation and CLI waves).

## Verified progress

- All seven submodule Rust ports are committed and building cleanly:

  | Crate | Path | Type | Status |
  |-------|------|------|--------|
  | fparser-rs | fparser/rust | lib | 52 tests pass, clippy clean, fmt clean |
  | csxcad-core | CSXCAD/rust | lib | 194 tests pass (200 with HDF5), including the native XML corpus, differential model harness and mesh fixtures; clippy and fmt clean |
  | csxcad-python | CSXCAD/rust-py | lib+package | 2 Rust tests plus 36 Python surface/contract tests; the native Python suite (150 tests) passes against it; installs as the native `CSXCAD` package |
  | csxcad-matlab | CSXCAD/rust-matlab | cdylib | 18 FFI functions with 7 contract tests; the Octave M-file surface test checks all 58 public + 12 private native M-files |
  | openems-core | openEMS/rust | lib | 238 + 2 tests pass, clippy clean, fmt clean |
  | openems-processing | openEMS/rust | lib | 10 tests pass, clippy clean, fmt clean |
  | openems-matlab | openEMS/rust-matlab | cdylib | 34 C-ABI entry points with 25 contract tests and 54 Octave checks |
  | openems-cli | openEMS/rust-cli | bin | Compiles cleanly |
  | qcsxcad-egui | QCSXCAD/rust-egui | lib | Compiles cleanly |
  | appcsxcad | AppCSXCAD/rust | bin | Compiles cleanly |
  | hyp2mat-rs | hyp2mat/rust | lib+bin | 114 tests pass (77 lib + 23 CLI + 14 fixture corpus); native differential model dump and `-v` summary byte-identical for all 9 fixtures |
  | ctb-rs | CTB/rust | lib+bin | 65 lib + 8 differential + 4 CLI + 1 doc tests; the `ctb` CLI plus Octave M-file wrappers are exercised in Octave 11.1.0 |

- Root Cargo workspace builds all 13 crates with proper dependency ordering
  (fparser → CSXCAD → openEMS → QCSXCAD → AppCSXCAD, hyp2mat after CSXCAD,
  CTB independent).
- Root CMakeLists.txt and update_openEMS.sh updated with 13 ExternalProject_Add
  entries for all Rust crates.
- csxcad-python: PyO3 Python bindings for csxcad-core, rewritten to match
  csxcad-core API (Primitive::box_primitive/sphere/point, PropertyId::from_u64,
  MaterialField::set_value).
- csxcad-matlab: C ABI cdylib wrapping csxcad-core Structure with 18 FFI
  functions for MATLAB/Octave MEX interop.
- openems-matlab: C ABI cdylib wrapping openems-core OpenEMS solver with 29
  FFI functions for MATLAB/Octave MEX interop.
- openems-processing: ProcessingArray integration with ProcessIntegral,
  ProcessVoltage, ProcessCurrent, ProcessFields structs and 10 new tests.
- openems-cli: Binary crate wrapping openems-core for command-line FDTD
  simulation.
- qcsxcad-egui: egui-winit/wgpu rendering crate for QCSXCAD GUI.
- appcsxcad: Binary crate with winit event loop for AppCSXCAD desktop app.

- Read the root `AGENTS.md`, `AI_POLICY.md`, and `readme.md`, plus the
  `AGENTS.md` files present in openEMS and CSXCAD. No `AGENTS.md` was found in
  the other five submodules.
- Inspected the root build graph, submodule roles, top-level source layouts,
  language/build-system indicators, and component summaries. The root build
  graph is recorded in `MIGRATION_PLAN.md`.
- The seven submodules contain C/C++ and/or Matlab/Octave sources; CSXCAD and
  openEMS also contain Python/Cython surfaces. The GUI components use Qt/VTK.
  hyp2mat uses autotools and CTB uses Make. The initial inventory found no
  Cargo workspace; the first standalone manifest now exists at
  `fparser/rust/Cargo.toml`. A root Cargo integration workspace is still
  future work.
- `COVERAGE_MATRIX.csv` maps all 27 source families to proposed Rust units.
  Detailed source and declaration inventories remain in the component audits;
  public CSXCAD/openEMS declaration coverage is cross-checked there.
- The fparser source/API pass is documented in `audits/fparser.md`; its default
  CMake target builds on this Windows host. Focused source-linked probes now
  cover evaluator errors, nested-parser propagation, inline variables,
  conditional branches, callback effects under optimization, precedence,
  units, degree mode, epsilon boundaries, and logical truth. Complex-double
  signed-zero behavior and all three complex scalar builds were also probed.
  The source-listed built-in function set and type/angle flags were inventoried.
  The generated optimizer table's 262 rules, grammar subsets, pipeline order,
  and available guard categories were also mapped; individual patterns remain
  opaque in the only tracked generated source.
  Every source-listed built-in was smoke-tested in the default double parser;
  exact values, complex-only parse behavior, and the `int`/`trunc` distinction
  are recorded in the audit. The complex-double parser also exercised all
  complex-only built-ins.
  The Rust crate now explicitly adopts an idiomatic `Result`-based API with an
  `f64` baseline rather than source-level `FunctionParserBase` compatibility;
  callback wrappers, debug bytecode hooks, optional numeric variants, and
  language bindings remain outside this crate's implemented surface.
  Source review found a wrapper-registration failure path that leaks the
  copied wrapper; it is documented as a confirmed submodule finding and was
  not changed in the root repository.
  MPFR/GMP wrapper source and precision/conversion boundaries were inspected;
  separate WSL C++98 builds and arithmetic probes now pass using preinstalled
  MPFR/GMP libraries. The source/API audit is complete with residual
  validation limits: individual generated optimizer rules remain unmapped,
  broader MPFR/GMP precision and packaging behavior is unverified, and
  cross-compiler complex behavior and broader type/domain cases remain
  unvalidated.
- Completed the CSXCAD native source audit in `audits/csxcad-native.md`.
  The model/property/primitive families, core raw-pointer ownership and
  transfer contracts, transform/parameter/grid roles, XML dispatch and legacy
  aliases, background defaults, box coordinates, and visible tests are mapped.
  Locale mutation, partial-read state, null-node behavior, and subclass-copy
  details remain compatibility questions, not confirmed defects. An earlier
  Windows CMake configure check stopped because the fparser include directory
  and TinyXML headers/library were unavailable; the later WSL baseline passed
  the two CSXCAD native tests. No dependencies were added to the repository.
- Began the CSXCAD Rust port in `CSXCAD/rust` as the standalone `csxcad-core`
  crate, depending only on the local `fparser-rs` path. Parameter evaluation,
  rectilinear-grid operations, 4x4 transforms, base structure/property/
  primitive ownership, parameterized points, boxes and multi-box unions,
  spheres, spherical shells, finite cylinders, cylindrical shells, curves,
  wires, polygons, linear- and rotational-extrusion polygons, polyhedra,
  standard STL/PLY PolyhedronReader imports, and User-Defined geometry with
  parameterized coordinate shifts and
  Cartesian/cylindrical/spherical containment expressions, plus isotropic/
  anisotropic material terms and
  weights are implemented. Absorbing-boundary property data includes the
  native defaults, expression-backed phase velocity, and round-trip-preserved
  boundary enum values. Cartesian/cylindrical conversion is included for
  these   primitive geometry operations. Dependency-free XML read/write covers
  a subset of parameters, grids, base property types and primitive families;
  145 default Rust tests pass; the optional HDF5 feature passes 148 tests,
  including version-2 database loading through the existing system HDF5 C
  library. Native zero-height cylinder and cylindrical-shell bounds and
  containment now match the point-degenerate C++ results. Fixtures emitted by
  the built native CSXCAD C++ library verify
  Rust parsing of default and parameterized grid/material/box XML; one also
  survives a complete Rust parse/serialize/parse equality round-trip. Native
  CSXCAD 0.7.0 also accepted Rust-serialized parameterized output without
  diagnostics and restored its grid lines, property, and primitive. The
  User-Defined primitive parser accepts both the native writer's hyphenated
  tag and the `UserDefined` spelling in the native C++ read dispatch, while
  the Rust writer keeps the native writer's spelling.
  Native CGAL probes confirmed rejection of repeated face vertices, overfull
  edges, facets attached to a closed vertex, facets joining disconnected
  vertex fans, and non-orientable facets; shells sharing only one vertex retain
  five of eight facets, while shells sharing an edge or face retain only the
  first four. Rust matches tested accepted-face counts, dimensions, and
  rejected-face containment, though full CGAL topology is not mirrored.
  A seeded native cube query also confirms that points on a
  face, edge, and vertex are classified as inside; the Rust containment
  regression matches those boundary and near-boundary results.
  Property copies now match the native default of excluding primitives, with
  an explicit option to include cloned primitives; tests verify copied
  metadata and fresh structure-owned handles after insertion. Structure
  queries support native property-type counts and filters, combined type
  masks, primitive counts, primitive-owner lookup, optional descending
  priority ordering, the native-stub-compatible primitive-type query,
  bounding-box queries, unused-primitive filtering, and grid-edge insertion.
  Simulation-setup
  prerequisite validation checks native structural gates, but does not replace
  native `Update()` validation of primitive/property contents. Property
  expression validation evaluates supported material, dispersion, conducting-
  sheet, absorbing-boundary, lumped-element and excitation terms and identifies
  the failing property. Primitive-bound evaluation reports parameter/transform
  errors with primitive identity, including unresolved wire-radius, shell-width,
  linear-extrusion, and rotational-polygon angle terms.
  User-Defined function syntax and coordinate
  shifts are validated, but the function is not sampled and other native
  shape-specific `Update()` checks remain open. A combined geometry validation
  method checks structural counts, primitive bounds, property expressions, and
  excitation presence in native guard order, preserving detailed error
  ownership.
  `clear()` resets the structure and preserves non-reuse of Rust-issued handles.
  Coordinate queries select the highest-priority containing primitive,
  individually or in batches, and
  optionally mark it used; property-filtered structure bounds union finite
  primitives and ignore unbounded User-Defined geometry.
  Bounding-box queries select intersections and conservatively include
  transformed or unbounded primitives.
  Strict XML parsing remains the default; a warning-returning compatibility
  method skips unsupported property tags, retains invalid recognized
  properties as `Unknown` when base metadata is valid, and skips unsupported
  or malformed primitive nodes and warns when a property has no primitive
  list or the `Properties` node is missing. It also skips unsupported and
  malformed parameter entries while retaining valid entries. Compatibility
  mode parses property visibility using the native integer attribute semantics.
  Rust `Unknown` properties now use the native hidden-by-default visibility
  and empty default property value, verified through XML output and re-import.
  In-memory discrete-material voxel-index and
  caller-provided scalar-value lookup with native coordinate conversion,
  transform/scale order, cell ordering, and background/out-of-range fallback,
  plus targeted STL/PLY point-order and face-index differential checks against
  VTK 9.5.2, including ASCII and binary PLY face lists with zero through three
  indices and the `vertex_indices`/`vertex_index` property aliases, as well as
  ASCII/binary PLY files with ignored edge elements containing scalar or list
  properties,
  STL/PLY PolyhedronReader imports, User-Defined primitive XML and containment,
  absorbing-boundary
  defaults and XML round-trips, lumped-element defaults and XML round-trips,
  ProbeBox and DumpBox sampling/mode-data round-trips, excitation parameter
  evaluation and XML round-trips, ResBox visibility/refinement factors, Debye
  DispersiveMaterial XML, Debye/Lorentz dispersion orders and coordinate
  weights, discrete-material file settings and transforms,
  shell and curve/wire behavior,
  polygon containment and extrusion, polyhedron solids, parsing of native-shaped
  XML, and round-trips for supported material and conducting-sheet properties,
  parameterized geometry, and property colors; emitted property IDs are
  normalized to native list indices.
  broader edge-case parity with VTK's STL/PLY readers, remaining model/XML
  compatibility, native
  differential comparisons, scripting integration, and full-stack compatibility remain
  outstanding; see `VALIDATION.md` and
  `COVERAGE_MATRIX.csv`.
- Completed the CSXCAD Python/Cython and Matlab/Octave interface map in
  `audits/csxcad-interfaces.md`. Ownership/identity and invalidated-wrapper
  behavior are source-mapped; all public Cython method names and all 114
  CSXCAD M-file declarations are cross-checked against the interface audit.
  MATLAB R2025b successfully wrote the documented metal-box XML example. The
  WSL baseline later built the Python extension; 150 CSXCAD Python tests
  passed with one skipped. Method-level defaults, errors, and conversions
  remain for consolidation, and the separate Octave XML writer has not been
  directly probed.
- Completed the CTB source audit and ran MATLAB numerical and file-format
  probes, recorded in `audits/ctb.md`. The probes confirmed a PI helper runtime
  failure, transposed 3+ port Touchstone round trips, and malformed extension
  acceptance. Extended probes covered singular transforms, invalid references,
  dimensions, malformed/truncated Touchstone data, and network-operation edge
  behavior. Additional three-frequency, asymmetric-reference probes
  round-tripped 2-port S/Y/Z and S/ABCD and 3-port S/Y/Z transforms with
  maximum absolute error below `4.3e-14`; two-frequency 2-port Touchstone
  S/Z/Y writer-reader round trips also passed exactly, including S versus Z/Y
  reference defaults. Three-port S renormalization between unequal per-port
  reference vectors and back passed with error `1.39e-16`; 3-port S-to-Z/Y
  conversions also matched direct matrix equations within `2.84e-14`, and
  unequal-reference renormalization preserved the computed Z matrix within
  `7.12e-15`. A single-frequency 2-port S/ABCD round trip passed within
  `1.25e-16`.
  Exhaustive
  cross-product/interoperability validation remains.
  No CTB code was changed.
- Completed the hyp2mat source and repository-fixture audit in
  `audits/hyp2mat.md`. The HyperLynx grammar, PCB model, CLI, MATLAB wrapper,
  and CSXCAD/PDF/QucsStudio exporters are mapped. QucsStudio output drops
  additional stackup layers, and the README's claim of QucsStudio input is
  not matched by the audited parser sources; this remains a compatibility
  question. The WSL baseline later built and installed hyp2mat and verified
  `hyp2mat --help`; no `.hyp` fixture was available for a conversion run.
- Completed the hyp2mat-rs Rust port in `hyp2mat/rust/`. The crate implements
  a hand-written recursive-descent .hyp parser (replacing Bison/Flex), PCB
  model types (board, stackup, vias, devices, pins, polygons), clipper2
  polygon operations, CSXCAD and QucsStudio output writers, and a clap-based
  CLI with binary entry point. `cargo build`, `cargo clippy`, and `cargo test`
  all pass (14/14 tests); the binary was verified end-to-end with a sample
  .hyp file for both csxcad and qucs output formats. The PDF writer remains
  stubbed because libhpdf is a C dependency and no new dependencies are added
  per house rules. See `COVERAGE_MATRIX.csv` for the updated status row.
- Completed the root build/CI/package source audit in
  `audits/root-orchestration.md`. The dependency graph, optional builds,
  package-manager dependency helper, Python environment modes, TinyXML source
  build, source tarball path, and Linux/macOS/FreeBSD/Windows CI coverage are
  mapped. Bash syntax checks passed for the root build script and all scripts;
  source-level findings include an ineffective Python `site` venv option and
  discarded `update_openEMS.sh` error details. A full WSL build and all
  baseline test results are recorded in `VALIDATION.md`; other CI platforms
  remain untested.
- Completed the openEMS core source audit in `audits/openems-core.md`. The
  update equations and extension ordering, engine defaults, conditional
  physics-extension setup, termination behavior, and test suite categories are
  mapped. MATLAB R2025b passed 17 pure-M-file checks. The WSL baseline later
  passed the complete 10-test Octave suite, including analytic solver checks
  and an all-engine field-dump comparison.
- Completed the openEMS processing source map in
  `audits/openems-processing.md`. FD HDF5/VTK output, field-processing
  scheduling, NF2FF, SAR data paths, and available tests are mapped. Field
  units/scaling and Rust differential tests remain unverified. The original
  solver and extensions are now built; the Python suite passed all 31 unit and
  simulation tests and the Octave suite passed all 10 cases.
- Completed the openEMS scripting-interface source map in
  `audits/openems-interfaces.md`. Python/Cython setup and port surfaces,
  Matlab/Octave execution and post-processing paths, and coverage are mapped.
  The callable inventory now covers the controller, port classes, NF2FF,
  mesh/utility helpers, SAR wrappers, and 96 M-file declarations across 76
  files. Per-method contracts remain for audit consolidation. The
  pure-M-file unit groups passed. An initial Python test attempt had nine
  import errors before dependencies were installed; the later WSL baseline
  passed all 31 Python unit and simulation tests, all 10 Octave suite cases,
  and the Python and Octave MSL smoke tests. The native solver and compiled
  extensions are now available in the isolated WSL environment. Core M-file
  setup/serialization and
  `RunOpenEMS`/parallel execution contracts are now mapped, including the
  source-only per-run filename and SSH error-reporting discrepancies. Source
  discrepancies remain marked for reference confirmation, not as verified
  defects. A declaration cross-check confirms all 96 openEMS M-file function
  names are now explicitly represented; most of these still lack complete
  per-method behavior and test maps. MATLAB R2025b FD/mesh HDF5 value
  round-tripping passed after normalizing vector orientation; the TD path
  failed because `ReadHDF5FieldData` receives `1/time` as an attribute name
  and uses it as an invalid struct field. The Octave HDF5 writer is explicitly
  unimplemented in source. An analytic MATLAB probe also confirmed
  `Dump2VTK`'s spherical vector conversion omits the radial contribution to
  Cartesian Y. Range selection, subsampling, analytic interpolation, and
  TD-to-FD conversion probes passed; an out-of-domain scalar range reproduced
  an indexing error. A MATLAB probe also reproduced `calcWGPort`'s
  `RefPlaneShift` failure because bare `beta` resolves to MATLAB's built-in
  function, and confirmed an empty legacy `AddMSLPort` `ExcitePort` string
  enables excitation. These results are in `VALIDATION.md`; they do not
  establish solver-output compatibility. Source contracts now also cover
  lumped, curve, MSL, CPW, stripline, coaxial, rectangular/circular waveguide,
  and the associated port-calculation dispatch paths. NF2FF/SAR M-file
  contracts now distinguish legacy versus compound HDF5 layouts, optional
  executable invocation and error paths; MATLAB reproduced the documented
  optional-radius mismatch in deprecated `AnalyzeNF2FF`. Queue/optimizer
  source contracts now map child-process serialization/polling and identify
  the unimplemented default optimizer branch plus ASCO/status handling risks.
  The Python `HDF5Dump` method map now records metadata/layout detection,
  compound and split-complex reads, legacy axis reordering, region and
  sampling state, FD lookup versus on-the-fly TD DFT, attribute precedence,
  and the existing synthetic-fixture test coverage. The earlier audit attempt
  lacked NumPy and the compiled CSXCAD extension; the later WSL baseline
  installed them and passed the principal test suites. No Rust differential
  result is claimed.
  The Python NF2FF constructor/calculation and result reader now have
  method-level maps for face/dump setup, cache checks, paired face-file
  analysis, legacy/current HDF5 axes, and derived far-field arrays. Synthetic
  reader tests are inventoried; native calculation/cache paths remain
  unvalidated against Rust or immutable reference outputs.
  Python SAR constructors/calculators and `readSAR` now have method-level
  contracts for constructor aliases, mass/method conversions, cube-stat
  enabling, input checks, result tuple contents, and delegated metadata/mesh
  behavior. SAR unit and analytic test cases are mapped, including frequency
  and thread consistency; the earlier audit attempt could not import its
  dependencies/native extension, while the later WSL Python baseline passed.
  The documented scalar
  Cartesian result contract is not independently enforced by `readSAR`.
  The Python automesh methods now have detailed source/test maps for axis
  selection, point/box hints, refinement switches, merge behavior, transformed
  boxes, and CFL timestep assumptions. Several branches lack direct tests,
  including point hints and CFL estimation; the principal Python suite passed,
  but those specific branches remain unverified.
  The `get_resource_path` helper is now source-mapped for bundled, source-tree,
  and installation-prefix search precedence, first-existing-path behavior,
  missing-resource errors, and CMake/wheel resource placement; no direct helper
  tests were found, and its specific direct runtime behavior remains
  unverified despite the later passing Python suite. Its MATLAB
  counterpart is mapped as a single function-relative `../resources` lookup
  with its own error identifier; MATLAB R2025b resolved a phantom from a
  changed working directory and raised the expected missing-resource error.
  Two tutorial callers were found, but no direct helper test or intentional
  cross-interface parity decision exists.
  The other standalone Python numerical utilities have source-level contracts
  but no dedicated unit assertions: observed uses are in simulation scripts,
  the MRI/radar tutorials, or NF2FF cache checks rather than utility-specific
  regression tests.
  Python/MATLAB physical-constant formulas and the native fixed literals were
  cross-checked; their computed differences are at decimal-rounding scale,
  while Python `C0` is an integer and MATLAB alone retains a lowercase `c0`
  alias. No dedicated constant tests were found.
  Controller test coverage is now distinguished by method: coordinate systems,
  multigrid validation, boundary-condition parsing, excitation forwarding, and
  CSX-dependent port dispatch have direct cases, while constructor-option
  tests assert construction only and `Reset`/cylindrical-coordinates/direct
  timestep setters have no direct test.
  Additional MATLAB utility contracts now cover `AR_estimate`, `FFT_time2freq`,
  `calc_ypar`, and external-process-backed `harminv`; the `FFT_time2freq`
  analytic transform group passed five checks with relative deviations below
  `3.2e-12`. `AR_estimate` passed constant extrapolation and input-error codes
  1/2/3/10; its unstable-fit and nonuniform-sampling cases remain untested.
  `harminv`'s executable is unavailable here (`harminv` is absent from `PATH`
  and the expected Windows location).
  M-file helper contracts now also include `AddPML`, `AddMRStub`, and
  `FindFreeSSH`; MATLAB confirmed directional and zero-count PML padding,
  while stub normal-vector handling and SSH polling remain source-only.
  NF2FF helper mapping now includes cache-axis comparison, compound-complex
  field reordering, plane-current integration, and the local 2-D trapezoid
  integrator. Source review identified matrix right-division in `vectorEqual`
  and an unused `center` argument in `process_plane`; a MATLAB R2025b probe
  reproduced `vectorEqual`'s mismatched-vector acceptance. The helpers have no
  direct reference tests.
  Unix queue process helpers are now mapped for output capture, PID polling,
  TERM/KILL escalation, and temporary-file cleanup. They cannot be executed on
  this Windows host and have no direct tests.
  The private openEMS launcher is also mapped for binary search, exit status,
  and platform-specific log handling; Octave `setup` and `ensure_oct_file`
  cover HDF5 oct-file compilation and load recovery. Source inspection found
  `setup` restores the working directory only after successful compilation.
  The specific launcher, compile-failure recovery, and platform-specific paths
  remain unexecuted; the principal solver and Octave suites passed in WSL.
  Additional M-file coverage now maps far-field VTK export and HDF5
  attribute/field/mesh access plus waveguide mode-file writing, including
  Octave layout and status-check limits; direct helper tests were not found.
  MATLAB R2025b confirmed the mode-file
  coordinate values, transposed component layout through `h5read`, and root
  version attribute. Final M-file example mapping now covers optimizer
  callbacks/cache keys, the directional-coupler post-processing helpers,
  CRLH mesh hints, patch-array setup, and the optimize path helper; no
  solver-backed examples or direct tests ran.
  The Python shared probe-file parser and base-port `ReadUIData`/`CalcPort`
  paths now have method-level contracts, including header parsing, summed
  probes, reference-impedance and reference-plane handling, and power outputs.
  The visible port suite covers constructor/geometry paths but does not
  directly test probe-file reading or port post-processing. A synthetic WSL
  probe passed header parsing/rejection, time-series summation, wave identity,
  and power assertions; solver-produced files, mismatched time axes, and
  reference-plane shifts remain unvalidated.
  Source contracts now cover `plotFF3D`, `plotFFdB`, `polarFF`, `plotRefl`,
  and `CleanupSimPath`. A focused WSL Octave probe passed cleanup-whitelist,
  unrelated-file preservation, and missing-directory creation assertions;
  genuine openEMS HDF5 fingerprint deletion and graphical output remain
  untested. A synthetic Octave HDF5 mesh probe confirmed Cartesian and
  spherical ordering but found cylindrical names remain alpha/rho while line
  arrays reorder rho/alpha, due to `fliplr` on a column-shaped `fieldnames`
  result; the finding is recorded for migration review.
- Extended the CSXCAD interface audit with method-level contracts for
  `CSProperties`/`CSPropMaterial`, dispersive/discrete material, excitation,
  absorbing-boundary, probe/dump, lumped-element, and conductor properties,
  the primitive base, common shapes, curve/wire/polyhedron/reader/multibox
  wrappers, `ContinuousStructure` operations, the background material, the
  direction utilities, mesh smoothing, rectilinear grid, and transform
  wrappers, including input coercion, defaults, assertion/error paths, array
  outputs, and visible test coverage. The stale wrapper-cache test comment
  claiming the structure leaks conflicts with the current
  `ContinuousStructure.__dealloc__` source; the targeted seven-test
  `test_WrapperCache` suite passed in WSL. Additional ownership-transfer paths
  remain to be directly validated. The compiled extension was unavailable
  during the initial audit; the later WSL baseline passed the principal
  CSXCAD Python suite. `InitCSX`, `DefineRectGrid`, and the
  MATLAB/Octave XML writer now have partial entry-point and serialization
  contracts, including source-level empty-value, escaping, and file-open
  differences. A MATLAB R2025b edge probe confirmed DOM escaping of ampersands
  in attributes and text and omission of an empty numeric field. Remaining
  CSXCAD method contracts still need detailed behavior coverage. A
  filename-to-audit cross-check confirms all 58 public and 12 private CSXCAD
  M-files are named in the interface audit; a second cross-check names all 33
  Cython classes.
  These inventory checks do not establish complete method behavior coverage. Additional
  M-file contracts now cover shared property/primitive construction, box,
  excitation, probe, dump, conducting-sheet, lumped-element, dispersive and
  discrete-material, and material-setting helpers. A MATLAB probe confirmed
  `AddProbe` reports an unknown option's value (`42` rendered as `"*"`) instead
  of its key; intended warning behavior remains a compatibility question.
  Primitive constructors are now grouped by emitted XML geometry and shared
  argument handling; these additional geometry paths remain source-only.
  Mesh smoothing/checking and excitation weighting helpers are also mapped;
  MATLAB confirmed quiet `CheckMesh` suppresses both warnings and returned
  error details. Analysis, edge detection, material calculators, discrete
  material HDF5 helpers, imports, and utility functions are also source-mapped.
  MATLAB reproduced the converter's undefined-`varagin` unknown-option path;
  its end-to-end raw-data workflow is unavailable, and a source discrepancy
  uses `dx` for Y/Z endpoint extension. Empire, Excellon, Gerber, and POV-Ray
  exporters plus `CSXGeomPlot` now have source-level workflow maps; multiple
  field/argument mismatches in the exporters remain untested. Property lookup,
  attribute, and plane-wave convenience helpers are also included in the
  M-file map. A focused `ContinuousStructure` source pass records
  writer/reader path-type asymmetry, uninspected variadic constructor arguments,
  `DefineGrid` mutation of the input mapping during smoothing, and that
  coordinate-priority lookup returns the property but not the native primitive
  out-parameter. These details remain source-only; the later WSL baseline
  passed the principal Python and Octave suites, but did not directly validate
  these specific behaviors.
  Private M-file helper contracts now separately map symmetry checks,
  property lookup and argument mutation, and the MATLAB DOM versus Octave text
  XML serializers. The focused XML probes cover escaping/empty values, but
  helper error paths, unsupported leaf values, and percent-bearing Octave XML
  content remain untested.
- Completed the QCSXCAD and AppCSXCAD GUI source map in `audits/gui.md`.
  Editing, tree/property/grid interactions, VTK rendering/export, XML I/O,
  Qt/VTK build conditions, and test coverage are mapped. No GUI tests are
  registered and interactive GUI validation was not possible in the headless
  WSL session. Two source defects and several compatibility questions are
  recorded without modifying either submodule. An earlier Windows CMake
  configure attempt stopped before Qt/VTK discovery because CSXCAD
  library/include paths and TinyXML were missing; the later WSL root build
  compiled and linked both GUI components.
- Consolidated confirmed source findings, open compatibility questions, and
  environment blockers in `AUDIT_FINDINGS.md`. The CSXCAD/openEMS interface
  audits now cross-check every M-file declaration and public-named Cython
  method; residual behavior and runtime gaps are listed explicitly.

## Outstanding gates and blockers

- Audit consolidation is complete for all root and submodule source families.
  Public interface declaration coverage is cross-checked for CSXCAD and
  openEMS. Behavior gaps that could not be exercised, platform-specific paths,
  TODO leads, and compatibility questions remain explicit in the component
  audits and findings; they are not presented as verified behavior.
- The full original stack and principal test suites now pass in Ubuntu WSL.
  Capped MSL/dipole references and converged 1D conducting-sheet and 3D coax
  references are preserved. Missing evidence includes interactive GUI
  behavior, builds on other CI platforms, additional workload diversity,
  generalized performance thresholds, and approved Rust comparison tolerances.
- TODO/FIXME markers were sampled, not adjudicated. They are leads for review,
  not verified defects or proof of missing functionality.
- The Rust architecture and migration sequence are recorded in
  `MIGRATION_PLAN.md`, with all 27 coverage-matrix families mapped. The initial
  `fparser/rust` crate implements a dependency-free f64 parser/evaluator, with
  52 passing unit tests and 36,717 C++ oracle differential expression cases
  (36,692 callback-count checks). It supports parser-to-parser links, the legacy
  Unicode whitespace set, and a measured subset of optimizer behavior,
  including legacy real-power semantics. Generated differential coverage
  includes operator/power grids over finite and non-finite values,
  boundary/magnitude sweeps for built-ins, and
  all 8,748 pairwise unary built-in compositions across optimized and
  unoptimized six-value input grids, plus 17,496 optimized and unoptimized
  compositions across a 12-value stress grid. Focused extreme-value cases
  cover `atan(tan(x))`, `abs(tanh(x))`, and `tanh(abs(x))`.
  GCC 15.2 and MSVC 19.44 produced identical C++ results in the complete
  118,098-case optimized triple sweep. Measured lowerings now cover
  `sec/tan(asin(cosh(x)))`, `tanh(acosh(cot(x)))`, nested `log2`,
  `cot(atan(x)) -> 1/x`, and the `sqrt(exp2(x))` exponential coefficient.
  C++ bytecode shows GCC uses `0.34657359027997259` and MSVC uses
  `0.34657359027997264` for the latter; the Rust lowering matches rounding
  results on both. The full triple audit now passes on Windows/MSVC 19.44 and
  Ubuntu WSL/GCC 15.2. The separate 236,196-case 12-value triple stress audit
  passes on both systems; equivalence for every generated optimizer rule is not
  claimed. macOS/FreeBSD runtime validation is outstanding. Optional
  numeric variants and malformed UTF-8 byte behavior are formally out of scope
  for `fparser-rs`: it accepts valid UTF-8 `str` and covers only the default
  real `f64` parser; the original C++ implementation remains the compatibility
  path for optional numeric configurations. Complete API compatibility remains
  open.
  Later component-specific compatibility, binding, GUI, and dependency choices
  remain scoped to their respective migration units.

## Next task

Waves A, C, D and E (CLI, Python, Octave/MATLAB, dumps, SAR, NF2FF,
QCSXCAD/AppCSXCAD, hyp2mat, CTB), the CSXCAD depth wave (RM-027/028/029/
034/035/036), the CSXCAD interface contracts (RM-031/032/033), the fparser
decisions (RM-023/024/025), the MATLAB C-ABI contracts (RM-094) and the CI
matrix (RM-026/030/120) are verified.

| Task | Work | State |
| --- | --- | --- |
| RM-121 | Performance baseline vs native | The harness and a first table exist; re-measure on the final solver (the curve-excitation fix and the threading threshold changed both solvers' work) and record it |
| RM-122 | Memory baseline vs native | Same run; peak RSS is already captured per case |
| RM-124 | Nightly reference run | The schedule and dispatch are in place; the first 03:00 UTC artifact is still pending |

Follow-ups found during the last validation pass, not yet tasks:

- `openEMS/rust/src/openems.rs` substitutes a default excitation where native
  `SetupFDTD` aborts with code 3 (recorded as a deviation in `VALIDATION.md`).
- `--nativeFieldDumps` (the VTK writer's native-vector mode) has no Rust
  equivalent yet; the CLI now exists, so this part of RM-144 is no longer
  blocked by a missing binary.
- The curve-excitation port unblocks the `SnapLine2Mesh` half of RM-144 once a
  consumer needs it (the GUI seam swap).

## Session record

### Canonical tree moved (2026-10-27)

The validation host deleted the `mberkanbicer-potential-garbanzo` worktree under
`.copilot/repos/copilot-worktrees` while the session was running. The tree was
re-cloned from GitHub to `D:\openEMS-Project-rust` on branch
`mberkanbicer-rust-migration-audit` (submodules at the recorded commits, full
history, not shallow). Every committed change survived; the only lost work was
an uncommitted `openEMS/rust/src/operator.rs` curve-excitation port, which was
restarted from the committed source. The WSL helpers no longer hard-code the old
path (they derive the repository root); the pinned native binaries
(`~/opt/openEMS`, `~/openems-exact`) and the `~/rustpy-venv` environment live
outside the tree and were unaffected.


- **Completed:** All seven submodule Rust ports committed and building cleanly
  (fparser-rs, csxcad-core, csxcad-python, csxcad-matlab, openems-core,
  openems-processing, openems-matlab, openems-cli, qcsxcad-egui, appcsxcad,
  hyp2mat-rs, ctb-rs). Root Cargo workspace builds all 13 crates. Root
  CMakeLists.txt and update_openEMS.sh updated with 13 ExternalProject_Add
  entries. Migration docs updated (MIGRATION_STATUS.md, COVERAGE_MATRIX.csv,
  VALIDATION.md).
- **Validation:** Coverage CSV parsed; whitespace and diff checks passed;
  Windows CMake build produced `fparser.dll`; default and opt-in scalar
  fparser examples ran, along with sine, constant-equality, and source-linked
  behavior probes covering semantics and all complex scalar configurations.
  The WSL original-stack build and component test results are listed under
  Baseline and in `VALIDATION.md`; the successful build includes Qt6/VTK GUI
  binaries, Python, CTB, and hyp2mat. Sphinx completed with zero warnings.
  MSBuild emitted warnings because its build/output directory was under
  `%TEMP%`, and the generated optimizer emitted narrowing warnings.
- **Unresolved:** Optional fparser backends and broader optimizer validation,
  cross-platform and interactive GUI testing, further reference diversity,
  final Rust tolerances, and component-specific compatibility decisions.

## Session record 2026-10-26 (differential reference harness)

- **Completed:** RM-117. `scripts/ci/reference_harness.py` runs the unmodified
  pinned Python sources against the Rust core, keeps the solver output and the
  exact `input.xml`, and compares the derived quantities with the native
  captures. `REFERENCE_TOLERANCES.md` records the proposed bounds and the
  measured values (RM-119, pending approval).
- **Found and fixed:** the D and B dumps were missing the absolute
  `EPS0`/`MU0` factor (native `m_epsR`/`m_mueR` store absolute values); the
  `et`/`ht` excitation waveforms were never written. Both are fixed in the
  submodule and covered by the source test / the MSL reference.
- **Found and tracked (not hidden):** conducting-sheet transmission is
  3.07 dB (RM-139), the FD dump disagrees with the FD probe by ~1.0 relative
  (RM-140), and the Python `AddMSLPort` excited-port current probes are all
  zero (RM-141). RM-135 returns to `Implemented` until RM-140 is fixed.
- **Validation:** Rust 229 openEMS (hdf5) + 2 CLI, Python 298 + 150, and the
  unmodified Octave suite 10/10 (459 s) pass after the changes.
- **Harness results:** coax PASS (`Z_ref` 7.5e-5, `S21` 1.9e-4 dB, `S11`
  0.05 dB); msl-notchfilter 8/10 checks pass (1.4e-8..6.0e-6); conducting
  sheet and fieldprobes FAIL on the tracked defects.
- **Next:** RM-140 (FD dump/probe), RM-139 (conducting sheet), RM-141
  (excited-port current), then RM-118/RM-119 and the rest of the list.

## Session record 2026-10-26 (Wave C closure, cylindrical operator)

- **Completed:** RM-134. The cylindrical `(rho, alpha, z)` operator reproduces
  the native `GetEdgeLength`/`GetNodeArea`/`GetEdgeArea`/`GetCellVolume`
  overrides, `load_csx` accepts `CoordSystem=1`, pins and pads a full `2*pi`
  azimuth, rejects negative rho, and `EngineExtCylinder` closes the seam after
  every voltage/current update. The `1/rho` excitation weight is evaluated in
  cylindrical coordinates and the UPML grading uses the cylindrical metric.
- **Validation:** `combinedtests/coax_cylindrical` PASS (beta 0.20 %, profile
  0.013 %, symmetry 7.6e-17). The unmodified native suite is now **10 passed,
  0 failed, 0 errors in 333.8 s**. Rust: 228 openEMS tests (hdf5 feature) plus
  the cylindrical metric/snap unit tests.
- **Records:** RM-134 Verified; RM-137 (`rho = 0` axis) and RM-138
  (cylindrical dumps) added as open tasks; ADR 0002 updated.
- **Next:** RM-137/RM-138 (cylindrical completeness), then the verification
  infrastructure (RM-117..RM-119) and the GUI/CTB waves.

## Session record 2026-10-25 (Wave B)

- **Completed:** RM-056 (Debye/Lorentz), RM-058 (lumped RLC), RM-059 (TFSF),
  RM-061 (cylindrical fail-loudly), RM-062 (multithreaded kernels), RM-063
  (`over_sampling`/`max_time`/threads/abort), RM-073 (SAR with 1 g/10 g
  averaging), RM-074 (NF2FF), RM-075 (mode matching), RM-082 (file-format
  documentation). RM-065 and RM-081 are implemented with partial evidence.
- **Science fixes:** the Yee dual-mesh convention, the CSXCAD single-value
  Debye/Lorentz vector replication, the missing Debye/Lorentz base material in
  the EC pipeline and the native per-cell `EC_C/EC_G/EC_L/EC_R` bookkeeping.
- **Validation:** `cargo test -p fparser-rs -p csxcad-core -p openems-core`
  passes; the openEMS suite has 211 library tests plus the 2 analytic
  integration tests. Evidence and tolerances are in `VALIDATION.md`; the
  task-level evidence is in `REMEDIATION_TASKS.md`.
- **Unresolved:** the three deferred analytic cases (Fresnel slab, anisotropic
  guide, graded dispersion), the byte-level dump comparison, and the blocked
  full-stack acceptance tasks that depend on the CLI/Python work.

## Session record 2026-10-25 (Wave C, CLI)

- **Completed:** RM-083 and RM-084. The `openEMS` binary now takes the native
  positional FDTD XML file, parses the `<FDTD>` element into the solver, and
  implements the native execution options (`--engine`, `--numThreads`,
  `--disable-dumps`, `--no-simulation`, `--dump-statistics`,
  `--exact-endcriteria`, `-v/-vv/-vvv`, the five `--debug-*` switches), the
  native exit codes (0/1/255) and the two statistics files.
- **Validation:** `openEMS/rust-cli/tests/cli_contract.rs` (6 tests) drives the
  built binary; the whole suite is now 438 tests, all passing.
- **Still open in Wave C:** RM-013 (native module names), RM-080 (Python
  HDF5/SAR/NF2FF readers), RM-085..RM-090 (native Python package and class
  surfaces), RM-091..RM-096 (MATLAB/Octave suite and the native test runs).
  The native Python package is ~6k lines of Cython plus ~2.3k lines of
  pure-Python modules; porting the class surface to PyO3 is the next block of
  work and was not started in this session.
