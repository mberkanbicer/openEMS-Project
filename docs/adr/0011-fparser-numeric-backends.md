# ADR 0011: fparser numeric backends (supersedes ADR 0006)

**Status:** Proposed 2026-11-01 (implementation not started)
**Decision owner:** Project owner
**Related:** E-001, RM-024, ADR 0006, D-06

## Context

ADR 0006 kept only `f64` and forbade a runtime backend abstraction. The owner
now asks for the native numeric variants: `float`, `long double`, long integer,
and the optional MPFR/GMP build. The native fparser selects them at compile
time, and openEMS/CSXCAD use the `double` build.

## Decision

Reintroduce compile-time numeric backends in `fparser-rs`, with `f64` remaining
the default and only backend enabled by dependents unless they opt in:

| feature | scalar | native equivalent |
| --- | --- | --- |
| default | `f64` | `double` |
| `float` | `f32` | `float` |
| `long-double` | `rug::Float` at 64-bit mantissa (x87 extended precision emulation) | `long double` |
| `mpfr` | `rug::Float` with runtime precision | MPFR build |
| `long-integer` | `i128` for the integer-only paths | long integer |

Rust has no stable 80-bit float, so `long-double` is an MPFR-backed 64-bit
mantissa value; the difference from x87 (exponent range only) is documented and
tested against the native `long double` build at the value level.

## Work breakdown

1. Introduce a `Real` scalar trait (`zero`, `one`, `from_f64`, arithmetic,
   `sqrt`, `powf`, trig, `is_nan`, formatting) and make the lexer, AST,
   evaluator and optimizer generic over it. `f64` is the first impl.
2. Add `f32` behind `float`; add differential tests against a native
   `-DDISABLE_LONG_DOUBLE`/`float` build of fparser on the existing 45k-row
   corpus with an f32-aware tolerance.
3. Add `rug` behind `mpfr`, with a precision argument on the parser handles;
   run the native MPFR fparser on the same corpus.
4. Keep the default build dependency-free; CI builds all features in separate
   jobs and runs the corpus per backend.
5. Document the precision/rounding differences and keep the `f64` public API
   source-compatible.

## Consequences

- The default solver path is unchanged (`f64`), so E-001's impact on openEMS is
  limited to scripts that explicitly select another backend.
- A new dependency (`rug`) is optional and feature-gated.
- The register gains a real differential suite per backend; no tolerance may be
  widened without a recorded cause.
