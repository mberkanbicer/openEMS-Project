# Legacy / non-Rust dependency register

Scope: every dependency that is not Rust source compiled by Cargo, and every
retained upstream implementation that is **not** linked into the Rust binaries.

| ID | Dependency | Kind | Used by | Boundary / safety | Licence | Evidence | Replacement status |
|---|---|---|---|---|---|---|---|
| LEG-001 | HDF5 C library (`libhdf5`) | native library | `csxcad-core`, `openems-core` with the `hdf5` feature | `extern "C"` wrappers in `CSXCAD/rust/src/hdf5.rs` and `openEMS/rust/src/hdf5.rs`; `Hid = i64` (not a 32-bit int); handles closed in `Drop`; errors mapped to `Hdf5Error` | HDF5 licence (BSD-style) | `cargo test --features hdf5`: 475 tests (recorded); feature-off builds keep the code out | **E-002 accepted**: no Rust-native HDF5 writer with the same compatibility |
| LEG-002 | Python runtime + PyO3 | language runtime / FFI | `csxcad-python`, `openems-py` | extension modules; NumPy arrays through the Python API; panic-free at the boundary (no `unwrap` across the module) | MIT/Apache-2.0 (PyO3), Python PSF | native Python suites 405 tests (after RM-168), 2 GPU tests skipped | required for the public Python API |
| LEG-003 | MATLAB/Octave C ABI | native ABI | `csxcad-matlab`, `openems-matlab` | thin `extern "C"` cdylibs, opaque pointers, `catch_unwind` around every entry; 34 exported symbols checked by `abi_inventory.rs` | project licence + MATLAB runtime terms | Octave testsuite 10/10, ABI tests | permitted adapter; the numerical core stays Rust |
| LEG-004 | `clipper2` → `clipper2c-sys` | C++ polygon clipping via FFI | `hyp2mat-rs` | crate boundary; used for PCB polygon boolean operations | GPL-3.0-or-later (hyp2mat) | hyp2mat tests 110; 9/9 byte-identical model dumps | **E-004**: `clipper2c-sys` has no FreeBSD target |
| LEG-005 | wgpu / winit / OS graphics | GPU + windowing APIs | `qcsxcad-egui`, `appcsxcad` | safe Rust wrappers; graphics only, **not** FDTD compute | MIT/Apache-2.0 | GUI tests + screenshots | required for the desktop surface |
| LEG-006 | Upstream C/C++ submodules | reference source, **not linked** | audit/reference only | no `cc`, `cmake`, `bindgen` or `links` in any Cargo manifest; the only `build.rs` use `pkg-config` to find HDF5 | upstream licences | `rg 'cc =|cmake =|bindgen|links ='` → 0; build.rs inspected | reference corpus per `AGENTS.md` §4 |

## Checks

- No production code invokes the native solver or any external executable:
  `Command::new` appears only in the two `build.rs` files (pkg-config).
- No Rust crate links `openEMS`/`CSXCAD` C++ objects; the install layout check
  reports the Rust binaries (`openEMS`, `AppCSXCAD`, `nf2ff`, `sar_calc`, `ctb`,
  `hyp2mat`).
- The submodules keep the upstream sources so that differential tests can run
  against the pinned native build; they are not part of the shipped Rust
  product.
- Every exception above has an entry in `docs/migration/EXCEPTIONS.md`
  (E-002, E-004) or is a permitted boundary in `AGENTS.md` §10 (Python/MATLAB
  API façades).
