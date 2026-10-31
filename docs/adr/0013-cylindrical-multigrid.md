# ADR 0013: cylindrical multi-grid

**Status:** Proposed 2026-11-01 (implementation not started)
**Decision owner:** Project owner
**Related:** E-007, native `Operator_CylinderMultiGrid`, `Engine_CylinderMultiGrid`

## Context

Native openEMS supports a nested cylindrical grid: a coarse base grid plus one
or more child grids with finer radial/azimuthal sampling, synchronized at each
time step. The port stores the radii (`set_multi_grid`, `MultiGrid=`), rejects
them at setup, and has no multigrid operator or engine.

## Decision

Port the native design rather than invent a new one:

1. **Operator layer** — `OperatorCylinderMultiGrid` holding the base operator
   and the child operator(s); the child grid is derived from the radii and the
   native refinement factors. Coefficients are assembled per grid with the same
   `AverageMatQuarterCell/CellCenter` rules.
2. **Compatibility rules** — port `IsCylindricalMultiGridSave`: extensions that
   cannot cross the grid interface (TFSF, some Mur faces, unsupported
   dispersive/port combinations) are rejected with a named error, exactly like
   native.
3. **Engine layer** — a multigrid engine that owns both field arrays and runs
   the update with the native barrier order: base update, child update,
   interpolation/restriction at the interface, extension hooks on both sides.
4. **Boundary/excitation** — PML and excitation on the base grid; the child
   inherits the physical boundary only where native does.
5. **Validation** — start from native reference cases:
   - a coaxial line with a radial refinement and probes on both grids;
   - a cylindrical cavity mode;
   - a multigrid model that native runs; compare probe traces and S-parameters
     node-by-node at the interface.
6. **Fallback** — until each piece is validated, `setup_fdtd` keeps rejecting
   radii (E-007 stays open). No silent single-grid fallback.

## Acceptance

- Native-equivalent fields/probes on the reference multigrid cases within the
  recorded f32 tolerance.
- Extension rejection matrix matches native (`IsCylindricalMultiGridSave`).
- E-007 closes only when the differential cases and the engine path are
  recorded in `VALIDATION.md`.

## Risks and effort

- XL: two operators, interface interpolation, synchronization and extension
  restrictions; likely several sessions.
- Thread/barrier semantics must match native order where results depend on it.
- Validation fixtures need native runs and a new convergence case.
