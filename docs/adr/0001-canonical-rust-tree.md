# ADR 0001 - Canonical Rust migration tree

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner (implementation authorised on 2026-10-24)
- **Related:** `docs/migration/REMEDIATION_PLAN.md` D-01, RM-001..RM-005

## Context

The repository contains two independent Rust implementations of the same
components:

1. `modernization/integration` (`a56e922`) keeps a three-crate workspace under
   the root `rust/` directory: `fparser-rs`, `csxcad-core` (811 lines, 3 tests)
   and `openems-core` (basic FDTD, 6 tests). It has no submodule ports, no
   bindings, no GUI, no processing.
2. `mberkanbicer-rust-migration-audit` (`205769d`) keeps the migration inside
   the owning submodules: `fparser/rust`, `CSXCAD/rust`, `openEMS/rust`,
   `QCSXCAD`, `AppCSXCAD`, `hyp2mat/rust`, `CTB/rust`, plus Python/MATLAB
   bindings. It has a 13-crate workspace and 328 passing numerical-core tests.

Both trees use the same crate names for different code. Keeping both is not
maintainable and makes every status statement ambiguous.

## Decision

The worktree on branch `mberkanbicer-rust-migration-audit` is the canonical
migration tree. All remediation work (WS0-WS10) happens there.

The three-crate `rust/` tree on `modernization/integration` is frozen. It is
archived with a tag before removal; no new code is written in it.

## Consequences

- `docs/migration/REMEDIATION_PLAN.md` and `REMEDIATION_TASKS.md` live with the
  canonical code.
- Submodule Rust commits must be moved from detached HEAD onto named branches
  and pushed before the root repository records new submodule pointers
  (RM-003, RM-004). Until then the canonical tree is local-only.
- Removing the duplicate (RM-002) is a destructive step and is not performed by
  this ADR; it requires the archive tag and an explicit confirmation.
- Status documents must name the canonical commit they describe.

## Alternatives considered

- **Keep the root `rust/` tree:** rejected; it duplicates only 3 of 13 crates
  and lacks every interface, GUI and processing component.
- **Merge both trees:** rejected; the code is not compatible and a merge would
  silently mix two different numerical implementations.

## Follow-up

1. Tag the frozen tree (RM-002).
2. Branch and push the submodule commits (RM-003).
3. Bump root pointers after the push (RM-004).

## Archive record (RM-002, 2026-10-25)

The frozen three-crate tree is preserved as tag
`archive/rust-3crate-tree-2026-10` on root commit `a56e922`
(`modernization/integration`). Its submodule pointers are:

| Submodule | Commit |
| --- | --- |
| fparser | `4b9c845b449b520c4b8c5f23c74cd04820084f81` |
| CSXCAD | `c46e3206f20027b0b4605c797d07bddab76de942` |
| openEMS | `305df56aa7df4d2f18c687083f484a96f9a22610` |
| QCSXCAD | `26d7ee13440cff0e5621a6b9d325ae31d118bc2d` |
| AppCSXCAD | `f04d3a7d7cce31c57704f14abe46c66684c15c7d` |
| hyp2mat | `b15f749849610066e6c09da5b5e3f97e3317ba8a` |
| CTB | `5ac29367ebb7e30e78dd3db13a21464756855599` |

The canonical tree contains exactly one definition of each shared crate
(`fparser-rs`, `csxcad-core`, `openems-core`); no duplicate sources remain.
The archive tag must be pushed with `git push origin archive/rust-3crate-tree-2026-10`
so the frozen state survives a fresh clone.

