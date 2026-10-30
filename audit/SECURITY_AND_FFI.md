# Security, unsafe code and FFI

## 1. `unsafe` inventory

`rg '\bunsafe\b'` over non-target Rust: **132 occurrences**.

| Crate | Occurrences | Context |
|---|---:|---|
| `openems-core` | 87 | HDF5 FFI; denormal/FTZ control; a `SendPtr` wrapper for the parallel engine; raw pointer stepping |
| `csxcad-core` | 26 | HDF5 FFI (`extern "C"`), handle lifetime |
| `openems-matlab` | 9 | C-ABI exports, opaque pointer checks |
| `csxcad-matlab` | 8 | C-ABI exports |
| `qcsxcad-egui` | 1 | platform/window call |
| `qcsxcad-core` | 1 | export path |

### Safety-critical spots

- `openEMS/rust/src/engine.rs:45-46`: `unsafe impl Send/Sync for SendPtr<T>`.
  The parallel stepping partitions disjoint field regions; the invariant is
  documented in the module and exercised by the 51-case harness. It remains a
  hand-audited invariant, not a compiler-checked one.
- `openEMS/rust/src/denormal.rs`: FTZ/DAZ control via `unsafe` intrinsics;
  covered by denormal tests.
- HDF5: `Hid = i64` (correct for 64-bit `hid_t`); every open handle is closed in
  `Drop`; FFI errors become `Hdf5Error`, not panics.

## 2. FFI boundaries

| Boundary | Mechanism | Panic containment | Ownership |
|---|---|---|---|
| HDF5 | `extern "C"` wrappers | no Rust panic across FFI; C errors mapped | RAII wrappers, `i64` handles |
| Python | PyO3 extension modules | PyO3 converts Rust panics to exceptions | Python owns arrays; no borrowed view after free |
| MATLAB/Octave | C-ABI cdylibs | every export runs inside `catch_unwind` | opaque `Box<Solver>` pointer; `null` checked on every call; delete is idempotent |
| GUI/GPU | wgpu/winit safe APIs | n/a (no FFI exports) | Rust ownership |

`abi_inventory.rs` checks 34 exported symbols against the native names, and
`contract_tests.rs` checks null/deleted pointers for the MATLAB surface.

## 3. Input handling

- XML is parsed by a hand-written parser (`CSXCAD/rust/src/xml.rs`), not an
  external DTD engine; malformed input returns `XmlError`.
- HDF5 datasets are shape/type checked before allocation; `hid_t` is 64-bit.
- Touchstone reader validates port count, frequency order and numeric fields
  (`CTB/rust/src/touchstone.rs`, differential tests).
- `hyp2mat` parses HyperLynx files with explicit record handling and fixture
  coverage.
- **SEC-001 (open)**: `fparser` is a recursive-descent parser with no explicit
  nesting-depth limit. A hostile expression with very deep parentheses can
  exhaust the stack. No fuzz corpus exists for fparser, XML, Touchstone or
  hyp2mat. Recommended: depth limit + `cargo fuzz` targets; not changed here
  because it alters parser error behavior and needs its own test corpus.

## 4. Runtime panics / unwraps

`rg '\.unwrap\(\)|\.expect\('` reports 2257 occurrences, mostly in tests and
fixtures. The production input paths inspected (XML/HDF5/Touchstone/CLI)
return `Result`; the GUI uses `expect` only for invariants on already-created
wgpu objects. A systematic `unwrap` audit is a P3 cleanup item.

## 5. Dependencies

- `Cargo.lock` is committed; the workspace pins egui 0.37 / wgpu 30 / winit
  0.30 / PyO3 0.30.
- `cargo audit` / `cargo deny` are not configured (no `deny.toml`); no advisory
  scan has been run in this audit. Recorded as a gap, not a pass.
- Licences: project crates LGPL-3.0-or-later/GPL-3.0 (hyp2mat); see
  `legacy_dependency_register.md`.

## 6. Not claimed

No Miri, ASan/TSan/UBSan, fuzzing or third-party penetration test has been run.
The unsafe audit above is a source review, not a proof of soundness.
