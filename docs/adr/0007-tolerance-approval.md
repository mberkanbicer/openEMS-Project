# ADR 0007 - Numerical tolerances require explicit approval

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-07, RM-119

## Context

Scientific equivalence cannot be reduced to "tests pass". Tolerances chosen to
make a failing comparison green would hide exactly the defects the migration is
supposed to prevent.

## Decision

Every numerical comparison must state its metric (absolute, relative, norm),
its value and the physical or numerical reason. Tolerances are approved and
recorded in `VALIDATION.md` before a component can move to `Verified`. A
tolerance may only be relaxed with a recorded justification; reference data may
never be edited to match output.

## Consequences

- Each validation entry names the test that enforces it.
- `Verified` requires both an executed comparison and an approved tolerance.
- Analytic checks are preferred where a closed-form result exists.
