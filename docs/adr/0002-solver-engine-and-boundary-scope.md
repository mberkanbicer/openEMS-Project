# ADR 0002 - Solver engine and boundary scope

- **Status:** Accepted, partially superseded
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-02, RM-042, RM-043, RM-061, RM-062

## Context

The C++ solver ships several engines (`basic`, `sse`, `sse-compressed`,
`multithreaded`) and several absorbing boundaries (Mur, UPML), plus cylindrical
operators and multi-grid variants. Porting all of them at once would spread the
verification effort too thin and risk silent numerical differences.

## Decision

Start with the basic Yee engine and the first-order Mur boundary. Implement UPML
next and only enable it after an absorption test passes. Defer SSE,
multi-threading and cylindrical/multi-grid support until the Cartesian basic
engine is verified.

## Consequences

- UPML was validated on 2026-10-24 (pulse residual 1.4e-6 of the peak, -117 dB)
  and is now enabled, superseding the "defer UPML" part of this decision.
- SSE and multi-threading remain open (RM-062).
- Cylindrical and multi-grid operators must fail loudly until implemented
  (RM-061); they must not silently fall back to Cartesian.
