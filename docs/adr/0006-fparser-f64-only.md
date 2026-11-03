# ADR 0006 - fparser numeric backends out of scope

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-06, RM-024, E-001

## Context

The native fparser can be compiled for `float`, `double`, `long double` and
`long integer`, with optional MPFR/GMP support. The openEMS solver uses the
`double` build only, and the Rust parser is used by CSXCAD expressions and the
solver.

## Decision

Port and maintain the `f64` numeric variant only. Record the other variants as
an approved omission; do not add a runtime numeric-backend abstraction.

## Consequences

- CSXCAD and openEMS expression evaluation are `f64`, matching the solver.
- Scripts that depend on `long double` precision or MPFR/GMP are not supported;
  this is recorded in `docs/migration/EXCEPTIONS.md` (E-001).
- Should a consumer need another precision, it is a new decision, not a silent
  extension.
