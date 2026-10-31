# Phase 2 plan: E-007, E-001, GPU, packaging

**Date:** 2026-11-01
**Scope:** the four items requested after the migration audit closed.
Status values follow `STATUS_POLICY.md`; only recorded evidence moves a row to
`Verified`.

| item | decision | status | next concrete step |
| --- | --- | --- | --- |
| E-008 `CellConstantMaterial` | implemented | **Verified 2026-11-01** | closed (differential operator dump, 278 lib tests) |
| Windows wheel version | abi3 wheel | **Verified 2026-11-01** | `cp39-abi3` wheel imports on 3.11 and 3.14; package rebuilt |
| E-001 fparser backends | ADR 0011 | Analyzed (design) | make the parser generic over a `Real` trait, then add `f32` |
| E-007 cylindrical multi-grid | ADR 0013 | Analyzed (design) | port the operator/engine pair and the extension matrix |
| GPU acceleration | ADR 0012 | Analyzed (design) | `wgpu` device layer + E/H kernels, CPU reference bound |

## Ordered work

1. **E-001, stage 1** — scalar trait over the 4.5k-line parser; `f64` only in the
   default build. Gate: existing 45k-row differential corpus unchanged.
2. **E-001, stage 2** — `f32` feature + native `float` differential run; then
   `rug`/MPFR and the 80-bit emulation.
3. **GPU, stage 1** — feature-gated `wgpu` context and buffers; no solver
   change. Gate: round-trip of a field array on the local adapter.
4. **GPU, stage 2** — E/H kernels on the cavity case against the CPU engine;
   measure the f32 bound.
5. **E-007, stage 1** — operator pair + compatibility matrix, no engine yet.
6. **E-007, stage 2** — multigrid engine and native differential fixtures.

## Rules

- The default build must not gain a GPU or MPFR dependency.
- Every feature is additive and reported by the CLI (`--features` build info).
- No item closes without a recorded differential or analytic result; the
  current exceptions stay open until then.
