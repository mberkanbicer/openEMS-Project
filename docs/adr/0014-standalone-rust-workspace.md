# ADR 0014: standalone root-level Rust workspace

- Date: 2026-11-03
- Status: accepted

## Context

Through the migration the Rust crates lived inside the C++ submodule trees
(`fparser/rust`, `CSXCAD/rust`, `openEMS/rust`, ...). The root cargo
workspace addressed them by submodule-relative paths, so a fresh clone
needed all seven C++ submodules initialized before `cargo build` could run,
even though nothing in the Rust build reads C++ sources. Two files reached
into submodule data at compile time (`appcsxcad` toolbar icons,
`qcsxcad-core` HDF5 fixtures), which hid the coupling until a build was
attempted with the submodules uninitialized.

## Decision

1. The fifteen crates move to a root-level `crates/` directory in the
   superproject; the root workspace addresses them directly. `cargo build`
   and `cargo test` are verified green with the submodules uninitialized.
2. The submodule trees stay in the repository as the read-only reference
   implementation (AGENTS.md Section 4). They are no longer part of the
   Rust build.
3. Compile-time assets move into the owning crates (`appcsxcad/images`,
   `qcsxcad-core/tests/fixtures`); the mapping and source commits are
   recorded in `crates/PROVENANCE.md`.
4. CI workflows and `scripts/ci/*` are repointed to `crates/*`.

## Consequences

- Fresh-clone Rust builds need no submodule update; the repo is, in the
  build sense, fully Rust.
- The submodule copies of the crates become historical snapshots; new Rust
  work happens under `crates/` only. Drift between the two is prevented by
  treating `crates/` as the sole canonical home (this ADR).
- Crate git history before the move lives in the submodule repositories;
  provenance is `crates/PROVENANCE.md`.
- The WSL acceptance scripts were repointed mechanically; a full WSL
  acceptance re-run at the new layout is the follow-up verification.
