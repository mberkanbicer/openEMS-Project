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
