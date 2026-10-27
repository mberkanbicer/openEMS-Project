# openEMS Solver and Physics Audit

**Status:** Solver/extension source map complete for the audited execution
path. The later WSL baseline passed the Python unit/simulation suite and the
10-case Octave suite, including four-engine dump comparison; detailed
equation-level and immutable Rust differential validation remain open. No
openEMS code was changed.

## Solver architecture

The solver pipeline described in `openEMS/AGENTS.md` is:

1. `openEMS::ParseFDTDSetup()` reads solver settings from the CSXCAD XML; the
   orchestrator's `SetupFDTD()` constructs the operator and engine.
2. `Operator::CalcECOperator()` builds equivalent-circuit coefficient arrays
   (`vv`, `vi`, `ii`, `iv`) over the Yee mesh and retains discretization lines.
   Specialized implementations cover SSE/compressed layouts, cylindrical
   coordinates/multigrid, and multithreaded execution.
3. `Engine` stores voltage/current fields in `ArrayLib::ArrayNIJK<FDTD_FLOAT>`.
   `FDTD_FLOAT` is `float`; the component index is followed by the 3D indices.
4. `ProcessingArray` and `Engine_Interface_Base` provide engine-independent
   simulation processing. Field dumps feed the separate `nf2ff/` library.

The base engine's `IterateTS` order is explicit in `FDTD/engine.cpp`: execute
pre-voltage extensions in reverse order, update voltages, run post-voltage
extensions in normal order, apply voltage modifications, then do the
equivalent pre/update/post/apply sequence for currents. `numTS` increments
after the current-side hooks. The voltage update multiplies each component by
`vv` and adds `vi` times the discrete curl of current; the current update
multiplies by `ii` and adds `iv` times the discrete curl of voltage. Current
updates omit the terminal y/z grid lines; voltage updates include all
configured lines.

Physics is organized as paired `Operator_Extension` and `Engine_Extension`
implementations. The documented families include PML, Mur and absorbing
boundaries, excitation, TFSF, Lorentz/dispersive materials, conducting sheets,
lumped RLC, cylindrical coordinates, and steady-state detection. Extension
priority controls pre/post ordering; declaration order alone is not a
contract.

`openEMS::Reset()` source defaults the engine type to multithreaded with
automatic thread count, end criterion to `1e-6`, oversampling to 4, timestep
method to 3, timestep to automatic (`0`), timestep factor to 1, and maximum
time to 0. All six boundary types default to 0 and PML size to 8. During
`SetupFDTD()`, material/geometry extensions are added only for matching
properties; a periodic excitation also requests steady-state detection with
probes. The maximum physical time is converted to an integer timestep limit
using `m_maxTime / dt`.

For type-0 excitation, the run reports energy-change end criteria and warns
when the timestep limit is reached first. The test-suite documentation
explains that ordinary end-criteria checks are wall-clock-paced, whereas
`--exact-endcriteria` checks at a model-derived interval for deterministic
record lengths. It records a Coax run varying between 1054 and 1560 timesteps
(51.10–51.53 Ohm against a 51.44 Ohm limit) without exact checks. This is
documented historical suite evidence, not a probe run in this audit.

## Evidence and limitations

The architecture and extension rules are cross-referenced in
`openEMS/AGENTS.md`; the field-update loops and extension order are visible in
`FDTD/engine.cpp` and `FDTD/engine.h`. The audited execution path and extension
families are mapped, but equation-level audits of each extension and engine
variant are not complete.

MATLAB R2025b listed the available suite cases: `unittests/port_setup`,
`unittests/transforms`, `probes/fieldprobes`, `combinedtests/Coax`, `cavity`,
`coax_cylindrical`, `msl_port`, `nf2ff_dipole`, `rect_waveguide`, and
`enginetests/engine_compare`. Running the two pure-M-file unit groups passed
all checks (12 port/setup checks and 5 transform checks; 2.3 seconds total).
The full simulation groups compare closed-form results; engine comparison
covers basic, SSE, SSE-compressed, and multithreaded implementations. These
unit tests are an executed baseline, not a solver simulation.

The original simulation build and scientific comparisons have not been run.
No `openEMS` executable was found on `PATH`, and MATLAB `which('openEMS')`
returned no solver executable. The MATLAB wrappers themselves are on the path.
The earlier CSXCAD configure attempt was blocked by unavailable fparser
headers and TinyXML, so this checkout cannot yet provide the installed native
dependencies required by openEMS. No dependencies were installed.

## Remaining audit work

- Trace setup XML attributes into operator construction, grid/cell
  coefficients, selected engine, and extension registration.
- Map boundary conditions, excitation, materials, dispersive/lumped models,
  and cylindrical-coordinate equations to source and tests.
- Compare base, SIMD, compressed, multithreaded, and cylindrical update
  implementations, including synchronization and field-layout invariants.
- Complete equation-level termination and steady-state behavior and establish
  analytical/reference cases before any Rust implementation.
- Run the full original solver tests/smokes once the pinned stack is buildable;
  preserve failures and numerical tolerances.

## Rust implementation notes (2026-10-27)

Two behaviour-level gaps were found and closed after the initial audit. Both are
recorded here because the audit's source map alone does not show them.

### Curve excitations need `Operator::FindPath`

`Operator_Ext_Excitation::BuildExtension` (`FDTD/extensions/operator_ext_excitation.cpp:235-288`)
has a special branch for `CSPrimCurve`/`CSPrimWire` primitives: containment
testing can never hit a one-dimensional primitive, so it walks the curve points,
calls `Operator::FindPath` (`FDTD/operator.cpp:391`) and excites every edge on
the resulting path. The Rust port originally only had the containment branch, so
an `<Excitation>` whose primitive was a `Curve` (the pattern used by
`combinedtests/cavity`) produced an identically zero field. The testsuite did not
catch it because `check_frequency.m` compares a spectrum against `max(val)`,
which is 0 for an all-zero trace, so the case passed vacuously.

`openEMS/rust/src/operator.rs` now ports `SnapLine2Mesh` (dual=false,
full=true), `Point_Line_Distance` with the cylindrical metric, the greedy
`FindPath` walk (native neighbour order, strict `foot`/`dist` comparisons), the
out-of-domain failure and the closure loop, and the curve branch of the
excitation setup including the hard-excite VV/VI zeroing.
`scripts/ci/run_curve_excitation_check_wsl.sh` compares the three cavity voltage
probes against native: peak differences 4.8e-5 / 9.2e-6 / 2.9e-5 and maximum
sample differences 1.6e-4 / 4.5e-5 / 1.2e-4 over 20000 steps.

### Threading granularity

The base engine starts and joins its worker set on every update. The native
multithreaded engine keeps an OpenMP pool alive, so the per-step thread cost is
negligible there. The Rust port measured 12.4 s with the threaded kernel against
2.6 s serial on the 9152-cell cavity case. `worker_count` now falls back to the
calling thread below 16384 cells per worker; the 2.1M-cell Coax case still uses
the threads (57 s against 131 s serial) and its output is byte-identical between
`--engine=basic` and `--engine=multithreaded`.

SSE/SSE-compressed remain a documented performance-only omission (ADR 0002); the
measured gap is recorded in
`docs/migration/reference-data/perf/performance-baseline.md`.
