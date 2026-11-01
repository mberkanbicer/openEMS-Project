# ADR 0011: fparser numeric backends (supersedes ADR 0006)

**Status:** Partially implemented 2026-11-01 (loat/f32 backend; long double, long integer and MPFR pending)
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
| `long-double` | IEEE binary128 (`f128`/libquadmath) | `long double` |
| `mpfr` | `rug::Float` at 256-bit mantissa | MPFR build |
| `long-integer` | not implemented (integer-only builtins/optimizer rules) | long integer |

Rust has no stable 80-bit float, so `long-double` uses IEEE binary128 (113-bit
mantissa) through libquadmath: it carries more precision than the native x87
long double (64-bit mantissa) and is validated against the native build at the
value level. The `mpfr` backend uses `rug::Float` at the native 256-bit default
and required the non-`Copy` scalar refactor; both are feature-gated off the
default `f64` build.

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
