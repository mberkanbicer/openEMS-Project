# ADR 0008 - C++ API and FFI compatibility surface

- **Status:** Accepted
- **Date:** 2026-10-27
- **Decision owner:** Project owner
- **Related:** RM-025, D-03, D-05, E-003

## Context

The native project is a C++ library and application set: `CSXCAD` and
`openEMS` expose C++ classes (`CSXCAD::ContinuousStructure`,
`CSXCAD::CSProperties`, `CSXCAD::CSPrimitives`, `openEMS::FDTD`, …) that other
C++ programs, the Python/Cython bindings and the MATLAB MEX layer link against.
The migration must keep every required user workflow working while the
implementation becomes Rust.

A header-compatible C++ re-implementation would freeze the old class layout,
inheritance graph and ownership model, and would force the Rust core to
reproduce C++ object lifetimes through a second ABI layer. That conflicts with
the migration rule to preserve semantics rather than syntax, and it would keep a
second public surface alive forever.

## Decision

1. **The Rust crates are the canonical implementation.** `csxcad-core`,
   `openems-core`, `fparser-rs`, `ctb-rs`, `hyp2mat-rs` and the GUI crates are
   the supported library surface.
2. **No C++ source- or binary-compatible wrapper is provided.** The native C++
   headers (`CSXCAD/*.h`, `openEMS/*.h`) are not re-exported, and there is no
   drop-in `libCSXCAD`/`libopenEMS` ABI. C++ consumers must use one of the
   supported surfaces below or a new decision must be taken.
3. **External surfaces are, in order of maturity:**
   - the command-line binaries (`openEMS`, `ctb`, `hyp2mat`, `AppCSXCAD`),
     which keep the native argument contracts;
   - the Python packages (`CSXCAD`, `openEMS`) with the native module and class
     names (`ADR 0006` scope: `f64`);
   - the MATLAB/Octave path: the `openEMS` CLI plus thin M-files (`ADR 0005`)
     and a narrow C ABI (`csxcad-matlab`, `openems-matlab`) only where direct
     structure access is required;
   - the CSXCAD XML file format, which stays the interchange contract.
4. **A C ABI may exist only as reviewed glue for a foreign runtime** (MATLAB
   MEX/Octave today). Every exported function must be owned by a named crate,
   documented, covered by a contract test, and listed in the interface audit.
   The C ABI is not a general C++ compatibility layer.
5. **Temporary FFI is tracked.** System HDF5 is the only remaining library FFI
   (`ADR 0003`, exception `E-003`); it is behind the `hdf5` feature and reported
   as `Hdf5Error::Unsupported` when absent. No other native library may be added
   without an ADR.

## Consequences

- C++ programs that link `libCSXCAD`/`libopenEMS` must be ported to one of the
  supported surfaces; the migration does not promise source compatibility for
  them. This is an accepted, recorded consequence of the Rust-native goal.
- The Python and MATLAB surfaces remain the compatibility contract, and both are
  verified against the native test material (`RM-085..RM-096`, `RM-031..RM-033`).
- Adding a new C ABI export requires a contract test and an interface-audit
  entry; adding a native library dependency requires a new ADR.
- The XML format remains the stable interchange, so projects written by native
  openEMS stay usable without recompilation.
