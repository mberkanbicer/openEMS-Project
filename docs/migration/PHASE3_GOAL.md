# Phase-3 goal: finish the remaining technical gaps

**Set:** 2026-11-01
**Status:** active - loop until every item below is verified or explicitly out of scope
**Owner:** project owner

## Out of scope (owner decision 2026-11-01)

**E-010 hosted CI**: hosted GitHub Actions runs are removed from the migration
plan. The accepted platform evidence is the local WSL2 full acceptance gate plus
the Windows build/package checks recorded in `ACCEPTANCE.md` and
`WINDOWS_PACKAGE.md`. No hosted CI workflow is required to close the migration.

## Remaining items and done criteria

| item | work | done when |
| --- | --- | --- |
| E-001 long-integer backend | native `FunctionParser_gmpint` semantics: integer literals (decimal/octal/hex), truncating division, integer-only builtins, integer optimizer mode | Rust/`rug::Integer` backend passes unit tests and the native 52-expression differential; default `f64` unchanged |
| E-001 extended backends | long-double (binary128) and MPFR/GMP: already implemented and differentially tested | 30/30 native differentials and 3/3 unit tests each |
| GPU with extension models | host-sync path: E/H kernels on the GPU, extensions on the CPU with downloads/uploads around each phase; `--gpu` CLI wiring | CPU/GPU field parity, a high-level excitation/PML probe run, and a recorded wall-time comparison; explicit failure when `--gpu` is requested without a device |
| E-015 operator-dump diagnostic | **accepted** (diagnostic-only, solver physics unaffected) | written disposition in `VALIDATION.md`/`EXCEPTIONS.md`; physical gates stay green |

## Gate

The loop is complete when every row above is `Verified` (or the item is
explicitly out of scope), the full acceptance run includes the fparser
long-integer differential and the GPU host-extension tests, and the working
tree is clean with the report committed.
