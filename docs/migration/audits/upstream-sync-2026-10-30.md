# Upstream sync and Rust port (2026-10-30)

**Question:** what changed upstream in `thliebig/openEMS-Project` since the
migration baseline, and how much of it is now in the Rust port?

## Baseline and target

| Tree | Baseline | Target |
| --- | --- | --- |
| Root | `974294b` (`v0.37.0`) | `38da98d` (`upstream/master`, 2026-10-24) |
| CSXCAD | `c46e320` (`v0.7.0`) | `626b99f` (8 commits) |
| openEMS | `305df56` (`v0.37.0`) | `d686f1d` (38 commits) |
| QCSXCAD | `26d7ee1` | `6a22e41` (2 commits) |
| AppCSXCAD | `f04d3a7` | `bcbc0ad` (3 commits) |
| fparser, CTB, hyp2mat | - | unchanged |

The main project (`modernization/integration`) merges the root history and
fast-forwards the four submodules to the upstream commits. The Rust audit
branches merge the same upstream commits; the Rust code lives in the
submodules' `rust/` trees and did not conflict with the C++ changes.

## Ported into Rust

| Upstream change | Rust location | Evidence |
| --- | --- | --- |
| `SetGaussExcite(f0, fc, dc_free)`, XML `DCFree="1"` (openEMS `d686f1d`) | `openEMS/rust/src/excitation.rs` (`gauss_dc_free`, `gauss_sample`, `calc_gauss_max_freq`), `fdtd_options.rs` (`FdtdExcitation::Gauss.dc_free`), `openems.rs` (`set_gauss_excite_with_dc`), `rust-py` (`set_gauss_excite(..., dc_free=False)`) | `dc_free_tests`, `dc_free_option_tests`, `upstream_parity_tests` |
| Timesteps limited to `INT_MAX` (openEMS `7badca4`) | `openems.rs::set_number_of_time_steps` | `the_timestep_count_is_limited_to_int_max` |
| Unknown `--engine` is an error (openEMS `c971899`) | `openems.rs::set_engine` returns `Result`; `rust-cli` exits non-zero | `an_unknown_engine_is_an_error` |
| Polyhedron vertices in double precision (CSXCAD `a61f740`) | `CSXCAD/rust/src/model.rs` (`PolyhedronPrimitive` stores `[f64; 3]`) | `polyhedron_vertices_keep_double_precision` |
| Drawing tolerance for every primitive and the tolerant polyhedron inside test (CSXCAD `4a2d385`, `33ab8ab`) | `Structure::drawing_tolerance`, `Primitive::is_inside_with_tolerance`, per-shape tolerance (box, multi-box, sphere, shell, cylinder, wire, polygon, rotational polygon), robust solid-angle polyhedron test | `drawing_tolerance_tests` (4), `polyhedron_vertices_keep_double_precision` |
| Operator drawing tolerance from the mesh (openEMS `db68e62`) | `Operator::drawing_tolerance` = `1e-3 * min mesh step`, used by the material lookup | `test_the_operator_sets_the_drawing_tolerance_from_the_mesh` |

Test counts after the port: `csxcad-core` 166 lib + 24 integration,
`openems-core` 269 lib, workspace `cargo check` clean. The existing boundary
assertions of the containment tests were updated to the new native semantics
(the surface counts as inside; nested and overlapping closed components are
the union).

## Already present before the sync

| Upstream change | Why it was already covered |
| --- | --- |
| Excitation does not fire before its delay (openEMS `d1fef7c`) | `EngineExtExcitation::sample_index` returns `None` while `ts < delay` |
| Transform matrix inversion without VTK (CSXCAD `3d7abb2`) | `transform.rs` has its own `invert`/`invert_matrix` |
| VTK writing without VTK (openEMS `d9ca3b6`) | `processing.rs` writes VTK directly |
| C++17 only, no VTK/CGAL/Boost (CSXCAD `626b99f`, `cf965e8`) | the Rust crates have no such dependencies |

## Not applicable to the Rust port

| Upstream change | Reason |
| --- | --- |
| GPU engine, HIP/Metal plugins, device listing (openEMS `c3a956b`, `170c71b`, `81ec4db`, `a5594df`, `c0ca95a`, `53a4264`, `6bb955d`) | no GPU engine in the Rust port (ADR 0002); recorded as a scope decision |
| CMake, packaging, CI, Windows package changes | build/packaging only |
| Documentation and changelog commits | the Rust changelog is maintained in the submodules |

## Deferred, with the reason

| Upstream change | Why it is deferred |
| --- | --- |
| `python/openEMS/compare.py`, the option-order fix, the HDF5 read performance work | Python convenience/packaging surface, not engine behaviour |

Each deferred row is a follow-up item; none of them changes the result of an
existing Rust test.

## Path note

The worktree moved from `D:\openEMS-Project-rust` to
`C:\Users\mberkanbicer\Projects\openEMS-Project-rust` on 2026-10-30. The
historical path in `REMEDIATION_PLAN.md` is the old location of the same tree.
