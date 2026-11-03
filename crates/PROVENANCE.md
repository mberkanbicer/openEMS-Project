# Crate provenance

The `crates/` workspace is the standalone, cargo-first home of the Rust
migration. Each crate was copied from the pinned rust-branch checkout of its
source submodule at merge `df25995` (2026-11-03). The full Git history of
every crate stays in the submodule repositories; this directory starts a
fresh history with the references below.

| crate | source path (submodule) | source commit |
| --- | --- | --- |
| `fparser` (`fparser-rs`) | `fparser/rust` | fparser `c9431813` |
| `csxcad-core` | `CSXCAD/rust` | CSXCAD `43f9e80` |
| `csxcad-matlab` | `CSXCAD/rust-matlab` | CSXCAD `43f9e80` |
| `csxcad-python` | `CSXCAD/rust-py` | CSXCAD `43f9e80` |
| `openems-core` | `openEMS/rust` | openEMS `272f1a6` |
| `openems-matlab` | `openEMS/rust-matlab` | openEMS `272f1a6` |
| `openems-py` | `openEMS/rust-py` | openEMS `272f1a6` |
| `openems-cli` | `openEMS/rust-cli` | openEMS `272f1a6` |
| `nf2ff-cli` | `openEMS/nf2ff-cli` | openEMS `272f1a6` |
| `sar-cli` | `openEMS/sar-cli` | openEMS `272f1a6` |
| `qcsxcad-core` | `QCSXCAD/rust` | QCSXCAD `e832b4f` |
| `qcsxcad-egui` | `QCSXCAD/rust-egui` | QCSXCAD `e832b4f` |
| `appcsxcad` | `AppCSXCAD/rust` | AppCSXCAD `e05821b` |
| `hyp2mat` (`hyp2mat-rs`) | `hyp2mat/rust` | hyp2mat `ded44d00` |
| `ctb` (`ctb-rs`) | `CTB/rust` | CTB `570847c` |

Assets moved out of the submodules with the crates:

- `crates/appcsxcad/images/*.png` (7 icons) — from `QCSXCAD/images/`
  (`exit`, `filenew`, `fileopen`, `filesave`, `filesaveas`, `viewmag+`,
  `viewmag-.png`); `app.rs` `include_bytes!` paths rewritten to `../images/`.
- `crates/qcsxcad-core/tests/fixtures/discrete_material_v2.h5` — from
  `CSXCAD/rust/tests/fixtures/`; the two `include_bytes!` call sites
  (`discrete.rs`, `tessellate.rs`) rewritten to `../tests/fixtures/`.

Build artifacts (`*.so`, `*.pyd`, `__pycache__`, wheels) were not copied;
maturin rebuilds the Python extension modules.

The C++ submodule trees remain in the repository as the read-only reference
implementation (AGENTS.md Section 4); the cargo workspace no longer reads
anything from them, so `cargo build` and `cargo test` work on a fresh clone
without `git submodule update`.
