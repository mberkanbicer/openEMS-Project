# AGENTS.md — openEMS-Project Rust Migration

## 1. Mission

This repository is a fork of the openEMS-Project meta-repository.

The primary goal is to migrate the complete openEMS scientific simulation software from C/C++ to modern, stable Rust.

This includes all required subprojects, numerical engines, geometry tools, GUI applications, Python bindings, MATLAB/Octave interfaces, build systems, file formats, and related functionality.

**The goal is a complete, scientifically correct, functionally equivalent, Rust-native implementation.**

This is not a partial port, a Rust wrapper around the existing C++ implementation, or an unrelated redesign.

Preserve the original architecture and workflows wherever practical.

Scientific correctness and completeness are mandatory.

## 2. Instructions and Priorities

These rules apply to all AI coding agents and contributors working on this fork.

Before changing anything, read:

- `AGENTS.md` — This document.
- `AI_POLICY.md` — Existing contribution and disclosure requirements, where applicable.
- `readme.md` — Original project information.
- https://docs.openems.de — Original documentation.
- The relevant subproject's `AGENTS.md`, if present.
- `docs/migration/MIGRATION_PLAN.md`
- `docs/migration/MIGRATION_STATUS.md`
- `docs/migration/COVERAGE_MATRIX.csv`
- `docs/migration/VALIDATION.md`

If migration documents do not exist, create them during the initial audit.

Do not invent audit findings or migration progress.

### Priority Order

1. Scientific and mathematical correctness.
2. Complete functionality and correct integration.
3. Numerical equivalence and reproducibility.
4. Data and interface compatibility.
5. Memory safety, reliability, and stability.
6. Performance and scalability.
7. Modern Rust implementation and maintainability.

Lower priorities must not be used to violate higher ones.

## 3. Repository Structure and Scope

The original repository is a meta-repository containing independent Git submodules.

| Subproject | Original Responsibility |
|---|---|
| `fparser/` | Mathematical expression parsing |
| `CSXCAD/` | Geometry, materials, XML CAD, and simulation structures |
| `openEMS/` | Core FDTD electromagnetic simulation engine |
| `QCSXCAD/` | Qt-based geometry and structure visualization |
| `AppCSXCAD/` | Qt desktop application |
| `hyp2mat/` | HyperLynx PCB data conversion |
| `CTB/` | MATLAB/Octave circuit and RF postprocessing tools |

Also examine:

- Root build orchestration and CMake configuration.
- `update_openEMS.sh` and installation scripts.
- Python packages, bindings, and native extensions.
- MATLAB/Octave scripts and interfaces.
- Documentation and examples.
- Tests and scientific benchmarks.
- External libraries and runtime dependencies.
- Optional components and platform-specific implementations.

This list is not necessarily complete.

Discover the actual repository contents and Git submodule structure before defining the final migration scope.

Do not assume that every submodule is active, correctly connected, or fully implemented.

## 4. Fork and Upstream Protection

The original C/C++ implementation must remain available as a reference.

### Mandatory Rules

- Do not modify, rewrite, delete, or replace original C/C++ sources during initial migration.
- Keep original submodules and their Git history intact.
- Do not overwrite original scientific implementations with unverified Rust code.
- Develop the Rust implementation separately, preferably in a dedicated Cargo workspace.
- Keep the upstream remote and fork remotes distinct.
- Never push migration work to upstream repositories without explicit authorization.
- Never change Git submodule pointers without a clear reason.
- Never commit a submodule pointer referencing an unavailable commit.
- Commit changes in the repository that owns them.
- Respect each subproject's license and attribution requirements.

The fork may evolve independently, but the original implementation must remain accessible for comparison.

If existing C/C++ code contains a confirmed defect, document it separately from Rust migration defects.

Do not silently reproduce known scientific errors or change expected behavior.

## 5. Complete Source Code Audit

Before migration, inspect the entire project systematically.

Analyze:

- Every relevant directory and source file.
- Classes, structs, functions, templates, macros, and interfaces.
- Algorithms, mathematical operations, and data structures.
- Dependency relationships and execution paths.
- Memory ownership and resource lifetimes.
- Configuration and build options.
- Feature flags and conditional compilation.
- Public and internal APIs.
- Cross-language integration.
- GUI and visualization components.
- Scientific input and output formats.

Identify:

- Missing or incomplete functions.
- TODOs, placeholders, and stub implementations.
- Incorrect API usage.
- Bugs and undefined behavior.
- Missing or disconnected function calls.
- Unwired components and interfaces.
- Deprecated libraries and unsupported technologies.
- Unused or duplicated implementations.
- Hidden dependencies and platform-specific assumptions.
- Functionality implemented but not exposed or reachable.

Inspect original implementations in sufficient detail to preserve their actual behavior.

Never assume that a successful build proves functional completeness.

## 6. Scientific Correctness — Critical Requirement

openEMS is scientific simulation software.

**Preserving validated scientific behavior is the highest technical requirement.**

### Mathematical and Physical Models

Identify and preserve all applicable:

- Maxwell equations and electromagnetic formulations.
- FDTD schemes and numerical update equations.
- Spatial and temporal discretization.
- Yee-grid staggering and field-component placement.
- Material properties and constitutive relations.
- Dispersive, anisotropic, and lossy material behavior.
- Mesh generation and coordinate systems.
- Boundary conditions and absorbing layers, including PML.
- Excitations, sources, and ports.
- Field interpolation and sampling.
- Near-field and far-field calculations.
- Frequency-domain transformations.
- S-parameters and RF network calculations.
- Numerical integration and postprocessing.
- Solver stability and convergence behavior.

This list is illustrative, not exhaustive.

Identify the actual implemented formulations before migration.

### Numerical Preservation

Preserve:

- Mathematical equations and numerical algorithms.
- Physical constants and units.
- Data types and numerical precision.
- Indexing and memory layout where numerically relevant.
- Initial and boundary conditions.
- Algorithm ordering where results depend on it.
- Floating-point assumptions.
- Stopping and convergence criteria.
- Time-step selection and stability constraints.
- Error handling and exceptional conditions.

Do not replace an existing numerical method with a different method merely because it is newer or easier to implement.

Scientific method changes must be treated as separate, explicitly justified work.

## 7. Scientific Reference and Differential Validation

Establish reference results using the original C/C++ project before migrating numerical components.

Preserve the original reference environment, inputs, configurations, compiler settings, and relevant dependency versions.

For every important numerical component:

1. Identify its mathematical purpose.
2. Record representative input cases.
3. Capture intermediate and final reference results.
4. Implement the Rust equivalent.
5. Run identical cases.
6. Compare numerical outputs.
7. Investigate every significant difference.
8. Record verification evidence.

### Numerical Comparison Rules

- Use exact or bitwise comparisons when feasible.
- Otherwise define justified absolute, relative, and norm-based tolerances.
- Handle near-zero values, complex quantities, and multidimensional fields correctly.
- Check numerical stability, error propagation, and convergence.
- Use analytical or independently validated results where available.
- Verify physical invariants and conservation properties where applicable.
- Never increase tolerances only to make failing tests pass.
- Never modify reference data to hide incorrect results.

Bitwise equality may not be possible across compilers, architectures, or parallel execution orders.

The acceptance criteria must reflect justified numerical equivalence, not arbitrary tolerances.

### Required Scientific Scenarios

Validate representative cases covering:

- Simple analytical electromagnetic problems.
- Material interfaces and heterogeneous media.
- Different mesh configurations.
- Boundary conditions and absorbing layers.
- Sources and excitation models.
- Ports and transmission structures.
- Time-domain field evolution.
- Frequency-domain outputs.
- S-parameters and postprocessing.
- Geometry import and simulation setup.
- Representative complete simulations.

Expand these scenarios according to the actual supported features.

Compare intermediate computational stages, not only final output files.

## 8. Rust Implementation Requirements

Use modern, stable Rust and appropriate Cargo tooling.

### Language and Code Quality

- Prefer idiomatic, safe Rust.
- Use ownership, borrowing, lifetimes, traits, and generics appropriately.
- Replace manual memory management with safe Rust mechanisms.
- Use clear data structures and explicit error handling.
- Avoid unnecessary cloning, allocations, and dynamic dispatch.
- Keep numerical code readable and maintainable.
- Use `unsafe` only when necessary, with documented safety invariants.
- Do not hide unsafe native behavior behind misleading safe abstractions.

### Migration Rules

- Preserve semantics, not C++ syntax.
- Do not copy C++ inheritance structures mechanically.
- Do not introduce unnecessary abstraction layers.
- Do not redesign working components without clear justification.
- Do not add speculative functionality.
- Do not simplify algorithms if accuracy or compatibility may change.
- Do not leave stubbed or disconnected code.
- Prefer Rust-native implementations over permanent C/C++ wrappers.

Temporary FFI may be used during controlled migration when justified.

Every temporary FFI dependency must be tracked until replaced or formally accepted as an exception.

### Dependencies

Research current stable Rust libraries and frameworks using official sources.

Evaluate:

- Maintenance and support.
- Scientific and numerical correctness.
- API stability.
- Cross-platform compatibility.
- Performance.
- Licensing.
- Security.
- Long-term maintainability.

Do not automatically select the newest dependency version.

Do not introduce dependencies without a clear technical purpose.

A library replacement must be validated before it replaces a scientific implementation.

## 9. GUI, Visualization, and Application Migration

The migration must cover the complete user-facing software, not only the solver.

Inspect and preserve all applicable:

- Desktop GUI functionality.
- Geometry editing and visualization.
- 2D and 3D rendering.
- Mesh visualization.
- Simulation configuration.
- Material and excitation editors.
- Menus, dialogs, toolbars, and shortcuts.
- Application state and user settings.
- Simulation progress and error reporting.
- Field visualization and postprocessing.
- Import/export workflows.
- Interactive controls and navigation.

For QCSXCAD and AppCSXCAD:

- Inspect all existing Qt functionality.
- Map widgets, events, signals, slots, and data flow.
- Select an appropriate Rust-compatible GUI strategy.
- Preserve user-visible behavior and integration.
- Validate geometry rendering and interaction.
- Verify GUI-to-solver communication.

Do not replace a complete GUI with a reduced interface or CLI-only implementation.

Do not introduce an unrelated web frontend or service architecture without a clear requirement.

## 10. Python, MATLAB/Octave, and Other Interfaces

Audit all supported language interfaces and bindings.

### Python

Preserve applicable:

- Public module and package interfaces.
- Functions, classes, and expected behavior.
- Numerical data types and array layouts.
- Exceptions and error handling.
- Installation and packaging.
- Supported scripts and user workflows.

Use appropriate Rust/Python interoperability tools.

Verify actual Python execution, not only successful package compilation.

### MATLAB/Octave

- Identify existing APIs and postprocessing functions.
- Preserve calculation results and data conventions.
- Preserve supported workflows and compatibility.
- Reimplement native components in Rust where required.
- Retain language-level scripts when necessary for external compatibility.
- Verify equivalent numerical outputs.

A Rust-native computational core may still expose Python, MATLAB, or Octave interfaces.

Required external language interfaces must not be removed merely to achieve a Rust-only source tree.

## 11. Data Formats and Compatibility

Inspect every supported data format and serialization path.

Preserve applicable:

- CSXCAD XML structures.
- Geometry and mesh formats.
- Project and configuration files.
- Simulation input and output formats.
- Binary field data.
- HDF5 and other scientific data formats, where used.
- MATLAB/Octave data exchange.
- Python data interoperability.
- Units, metadata, precision, and coordinate conventions.

Existing valid simulation projects must remain usable.

Verify read/write compatibility and round-trip correctness where applicable.

Never silently change file schemas or numerical interpretation.

## 12. Performance and Parallel Computing

Establish performance baselines before major changes.

Inspect:

- Numerical kernels.
- Memory access patterns.
- CPU vectorization.
- SIMD behavior.
- Multithreading.
- OpenMP or other parallel implementations.
- GPU acceleration where applicable.
- Memory allocation and data movement.
- Solver scalability.
- Large-model resource consumption.

Preserve or improve performance where practical.

Evaluate performance using representative scientific workloads.

Correctness comes before optimization.

Do not introduce parallelism or unsafe optimization that changes numerical behavior beyond accepted tolerances.

Report meaningful performance regressions explicitly.

## 13. Build, Installation, and Platform Support

### Original Reference Build

The existing unified build uses root-level CMake and installation scripts.

The documented reference command is:

```bash
./update_openEMS.sh ~/opt/openEMS --python --with-CTB
```

Relevant existing options include:

- `--python`
- `--with-CTB`
- `--disable-GUI`
- `--njobs=N`
- `--verbose`
- `--with-tinyxml`

Inspect actual supported options before use.

Read generated build logs when diagnosing failures.

Build individual subprojects directly when appropriate.

Do not modify the original build process solely to make Rust migration easier.

### Rust Build

- Use Cargo workspaces where appropriate.
- Organize crates according to actual component boundaries.
- Preserve required operating systems and architectures.
- Support GUI and headless builds where needed.
- Document native dependencies and platform limitations.
- Verify clean builds, installation, and execution.
- Preserve reproducible dependency resolution.
- Use CI for supported build and validation configurations.

Do not claim platform support without verification.

## 14. Documentation and Existing Tests

The original documentation is maintained in `doc-src/` using Sphinx/RST.

Preserve the original documentation and generated content.

Do not manually edit generated documentation.

The original smoke tests include:

```bash
cd openEMS/.github/smoketests/octave
octave MSL_NotchFilter.m
```

```bash
cd openEMS/.github/smoketests/python
python3 MSL_NotchFilter.py
```

Additional suites exist in subprojects, including:

- `openEMS/TESTSUITE/`
- `CSXCAD/python/tests/`

Inspect the current repository before relying on exact paths.

Use these tests as part of the reference validation strategy.

Check documentation warnings, missing Python imports, and omitted generated API pages.

A successful documentation build exit code alone is not sufficient evidence of complete documentation.

## 15. Mandatory Migration Records

Maintain the following version-controlled files:

### `docs/migration/MIGRATION_PLAN.md`

Include:

- Complete migration scope.
- Architecture and dependency analysis.
- Migration phases.
- Component ordering.
- Technical decisions.
- Risks and acceptance criteria.

### `docs/migration/MIGRATION_STATUS.md`

Include:

- Current phase.
- Completed and verified work.
- Implemented but unverified work.
- Current tasks.
- Blockers and known issues.
- Last verified milestone.
- Exact next task.
- Session handoff information.

### `docs/migration/COVERAGE_MATRIX.csv`

Track:

- Original file and function.
- Original component or subproject.
- Rust file and function.
- Dependencies.
- Implementation status.
- Integration status.
- Validation status.
- Evidence and notes.

### `docs/migration/VALIDATION.md`

Record:

- Scientific reference cases.
- Baseline environments.
- Numerical comparison methods.
- Accepted tolerances and justification.
- Test results.
- Known numerical discrepancies.
- Verification evidence.

These files are the persistent project record.

Do not use conversation history as the only source of migration state.

## 16. Mandatory Development Workflow

### Phase A — Audit

Before implementation:

1. Inspect the full repository and submodules.
2. Understand architecture and scientific workflows.
3. Identify all functions, features, and interfaces.
4. Find incomplete and incorrect implementations.
5. Build a complete dependency map.
6. Establish the migration coverage matrix.
7. Record missing or unverified information.

### Phase B — Reference Baseline

1. Build the original project.
2. Run existing tests.
3. Execute representative scientific simulations.
4. Capture reference outputs.
5. Record build environment and numerical settings.
6. Identify existing defects separately.

Do not assume the original software is scientifically correct solely because it runs.

### Phase C — Migration Planning

1. Define Rust crate boundaries.
2. Select justified dependencies.
3. Determine component migration order.
4. Identify GUI and interface requirements.
5. Define validation methods.
6. Specify acceptance criteria.
7. Document unavoidable compatibility exceptions.

Do not begin uncontrolled large-scale rewriting.

### Phase D — Incremental Implementation

For each migration unit:

1. Read the original implementation.
2. Identify its exact behavior and dependencies.
3. Define required inputs, outputs, and edge cases.
4. Implement the complete Rust equivalent.
5. Integrate related components.
6. Build and run focused tests.
7. Compare against original reference behavior.
8. Fix discrepancies.
9. Update migration records.

Proceed according to dependency order.

### Phase E — System Integration

Verify:

- Geometry and mesh processing.
- Material and excitation setup.
- Solver execution.
- Output generation.
- Postprocessing.
- GUI integration.
- Python and MATLAB/Octave interfaces.
- File compatibility.
- Complete user workflows.

### Phase F — Final Verification

Verify complete scientific, functional, platform, and performance requirements.

Do not mark the full migration as complete while required components remain missing or unverified.

## 17. Definition of Done

A migration unit is complete only when:

- Its original behavior has been fully analyzed.
- Required Rust functionality is implemented.
- All required connections and interfaces work.
- The affected Rust components build.
- Relevant functional tests pass.
- Scientific equivalence is verified where applicable.
- No required features are missing or stubbed.
- Migration records contain verification evidence.

Use these status values:

- `Not Started`
- `Analyzed`
- `Implemented`
- `Integrated`
- `Verified`
- `Blocked`

**Only `Verified` counts as completed migration coverage.**

If tests cannot be executed, record the reason and leave the component unverified.

## 18. Context Recovery and Session Continuity

At the beginning of every new session:

1. Read this `AGENTS.md`.
2. Read the migration plan and current status.
3. Inspect the coverage matrix.
4. Review relevant scientific validation records.
5. Check the actual Git and working-tree state.
6. Identify the last verified milestone.
7. Resume from the next dependency-ready task.

At the end of every work session:

1. Record modified files.
2. Record completed implementation work.
3. Record tests and their actual results.
4. Update coverage and verification status.
5. Record blockers and unresolved issues.
6. Specify the exact next action.

Do not assume previous conversation context is available.

Do not overwrite reliable existing status records with guesses.

## 19. Git, Commits, and Contribution Rules

Preserve the original repository contribution requirements where applicable.

Follow `AI_POLICY.md` when preparing contributions governed by that policy.

For changes intended for upstream submission:

- Respect upstream licensing and contribution rules.
- Use the required AI-assistance disclosure.
- Follow the required sign-off and commit conventions.
- Keep logical changes separate.
- Commit subproject changes in their owning repositories.
- Update submodule pointers only after commits are available.

For fork-only migration work:

- Use clear, focused commits.
- Keep original and migrated code changes distinct.
- Do not mix unrelated modernization with scientific migration.
- Record important migration decisions.
- Never commit generated build output, temporary files, or local configuration.
- Never rewrite upstream history.

Do not assume that fork-specific Rust work is automatically suitable for upstream submission.

## 20. Strict Prohibitions

Never:

- Silently skip required source files or functions.
- Replace scientific calculations with approximate shortcuts without approval and validation.
- Change governing equations or solver behavior without explicit justification.
- Introduce numerical differences without investigation.
- Hide failing tests or unexplained discrepancies.
- Remove required GUI or API functionality.
- Use placeholders as completed implementations.
- Add unnecessary abstractions or architectural complexity.
- Introduce dependencies without technical justification.
- Modify the original reference implementation to force test agreement.
- Treat compilation as proof of scientific correctness.
- Report unsupported platforms as tested.
- Mark unverified functionality as complete.
- Delete original C/C++ implementations before replacement verification.
- Declare full migration while required work remains incomplete.

## 21. Final Acceptance Criteria

The project-level Rust migration is complete only when:

1. All required original components are accounted for.
2. Required functionality has a complete Rust implementation.
3. All main and subproject integrations work.
4. The scientific engine produces validated equivalent results.
5. Numerical accuracy, stability, and convergence requirements are satisfied.
6. GUI and visualization workflows are functional.
7. Required Python and MATLAB/Octave interfaces work.
8. Existing supported input and output formats remain compatible.
9. Supported target platforms build and run successfully.
10. Critical performance requirements are met.
11. No required functionality remains missing, stubbed, or disconnected.
12. Remaining native dependencies and accepted exceptions are documented.
13. Every required migration component has traceable verification evidence.

## Final Principle

**Audit completely. Preserve scientific behavior. Migrate systematically. Verify rigorously. Track every component.**

The goal is not simply to make openEMS compile in Rust.

The goal is to deliver a complete, reliable, scientifically validated Rust implementation of the original openEMS software ecosystem, without losing required functionality, accuracy, or compatibility.