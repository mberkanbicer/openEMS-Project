# Status and evidence policy

**Status:** approved 2026-10-29.
**Scope:** every record in `REMEDIATION_TASKS.md`, `MIGRATION_STATUS.md`,
`COVERAGE_MATRIX.csv`, `VALIDATION.md` and the per-component audits.

## Status vocabulary

Only these six values are used. There is no seventh value and no informal
variant.

| Status | Meaning |
| --- | --- |
| `Not Started` | No work begun |
| `Analyzed` | Source behaviour understood and recorded, no implementation |
| `Implemented` | Code exists and is reachable from a real entry point |
| `Integrated` | Wired into the product path (CLI, library, GUI, binding) |
| `Verified` | Executed comparison against a reference/analytic result, with an approved tolerance |
| `Blocked` | Cannot progress; the blocker is recorded with a reason |

`Blocked` means an **external** dependency (a missing display, an account
restriction, a decision only the owner can make). Work that is merely not done
stays `Implemented`. The earlier use of `Blocked` for unfinished code (RM-144)
was corrected on 2026-10-29.

## Evidence rules

1. A task may only move forward with evidence in its `Evidence` column. The
   evidence names a test or a command and its result.
2. Compilation is not verification. A numerical component reaches `Verified`
   only through an executed comparison recorded in `VALIDATION.md`.
3. A tolerance is only changed with a recorded justification; reference data is
   never edited to make output match (ADR 0007).
4. Accepted scope reductions live in `docs/migration/EXCEPTIONS.md`, never only
   in a conversation or a commit message.
5. Where the plan, the task list and `MIGRATION_STATUS.md` disagree, the task
   list is authoritative and the others are corrected in the same change.
6. A `Verified` row names a command that can be re-run on the current revision.
   A one-off measurement is recorded in `VALIDATION.md` but does not by itself
   close a row.

## Tolerance approval

Differential bounds live in `REFERENCE_TOLERANCES.md`. A bound may change only
together with a recorded measurement that justifies it and an owner-approved
decision in `VALIDATION.md`. A failing case is never resolved by widening its
bound. Bounds that already exist (for example the 1 % RMS probe bound) cover
new cases of the same kind without a new approval.

## Acknowledgement

| Name | Role | Date | Scope |
| --- | --- | --- | --- |
| Mustafa Berkan BICER | repository owner | 2026-10-29 | this policy, the closed vocabulary and the evidence rules |

The acknowledgement was recorded by the migration work on the owner's
instruction of 2026-10-29 to complete the remaining tasks; the owner can amend
or replace this table at any time.
