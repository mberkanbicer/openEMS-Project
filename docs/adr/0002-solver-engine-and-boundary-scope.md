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
- The cylindrical operator is implemented for the rectilinear
  `(rho, alpha, z)` mesh in 2026-10-26 (RM-134): the native edge/face metric,
  the closed-azimuth seam and the `1/rho` excitation weight are ported, and
  `combinedtests/coax_cylindrical` passes (beta = k0 within 0.20 %, radial
  profile within 0.013 %, exact rotational symmetry).
- Still deferred, and rejected loudly instead of silently degrading:
  a mesh that includes the `rho = 0` axis (RM-137) and cylindrical field
  dumps with the native `/Mesh/{rho,alpha,z}` layout (RM-138). The
  multi-grid variants remain out of scope.
