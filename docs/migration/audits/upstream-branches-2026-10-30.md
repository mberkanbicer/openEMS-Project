# Upstream branch scan (2026-10-30)

**Question:** which work lives on branches other than `master` in
`thliebig/openEMS-Project` and its subprojects, and what of it is applicable
to the Rust migration?

All remotes were fetched with `+refs/heads/*` and every branch was compared
with `upstream/master` (`38da98d`, CSXCAD `626b99f`, openEMS `d686f1d`).

## Branch inventory

| Repository | Branch | Ahead | Behind | Unique work |
| --- | --- | ---: | ---: | --- |
| root | `CI_testing` | 0 | 0 | none |
| CSXCAD | `WIP` | 13 | 0 | viewer GUI, Python `CSXCAD.Viewer`, MATLAB `csxcad-view`, nested-structure read, black edge default, Python render/probe getters |
| CSXCAD | `qtViewer` | 2 | 48 | 2022 Python-GUI experiment, obsolete |
| CSXCAD | `CI_testing` | 0 | 0 | none |
| CSXCAD | `python` | 0 | 231 | none |
| CSXCAD | `fix/issue-83-object-lifetime` | 0 | 31 | already in `master` |
| openEMS | `WIP` | 15 | 12 | Python `Results`/figures, `openems-view`, tutorial galleries, ports after `ReadFromXML`, debug-PEC edges |
| openEMS | `memory-stats` | 1 | 54 | `--debug-memory` array/RSS accounting |
| openEMS | `py_gui` | 1 | 364 | 2022 experiment, obsolete |
| openEMS | `CI_testing` | 0 | 6 | none |
| openEMS | `python` | 0 | 448 | none |
| openEMS | `fix/issue-83-object-lifetime` | 0 | 116 | already in `master` |
| QCSXCAD | `CI_testing` | 0 | 1 | none |
| AppCSXCAD | `CI_testing` | 0 | 0 | none |
| fparser | `CI_testing` | 1 | 0 | CI: drop the Debian oldoldstable job |
| CTB | `master` only | - | - | - |
| hyp2mat | `stable` | 0 | 18 | none |

Only `CSXCAD/WIP`, `openEMS/WIP` and `openEMS/memory-stats` carry work that is
not on `master`.

## Ported to Rust in this pass

| Branch commit | What | Rust change |
| --- | --- | --- |
| CSXCAD `271ed6b` | `ReadFromXML` finds a `ContinuousStructure` element anywhere in the document | recursive `find_descendant` in `CSXCAD/rust/src/serialization.rs`; test `a_structure_embedded_in_a_larger_document_is_found` |
| CSXCAD `c18abc8` | a new property's edge colour defaults to black, not its fill colour | `DEFAULT_EDGE` in `QCSXCAD/rust/src/tessellate.rs` is black, matching the native viewer |
| openEMS `ac21861` (`memory-stats`) | `--debug-memory` reports the array memory and the peak RSS, per FDTD cell | `openEMS/rust/src/memory.rs` (`PeakResidentBytes`), `Operator::memory_bytes`, `OpenEMS::show_memory_stat`, `--debug-memory` flag; test `the_memory_report_lists_the_operator_arrays` |
| fparser `a63b271` (`CI_testing`) | drop the Debian oldoldstable CI job (EOL, mirrors gone) | applied to the main project's fparser branch; it is CI configuration, so the Rust tree is unaffected |
| CSXCAD `3861b71` | disc-material/background surface as plain points and quads (`GetPolyDataModel`) | `DiscreteMaterialGrid::surface_poly_data` + `DiscreteMaterialSurface` (flat VTK helpers); `disc_surface_tests` (3) |
| openEMS `eb1c5ee` | energy end criteria every Nyquist period during the first 60 s, wall-clock afterwards | `EXACT_ENDCRIT_TIME`, `end_criteria_due`, plus the updated cadence test |
| openEMS `367a63f` | flush denormals to zero during the run, restore the caller's setting | `denormal::FlushToZero` guard used by `run_fdtd`; `the_denormal_flush_is_set_and_restored` |
| openEMS `a0d5c87` | debug-PEC edges with their direction and length unit | `Operator::pec_edges` + `debug_dump::write_pec_edges_vtp` (`PEC_dump.vtp`, `direction`, `LengthUnit`); `the_pec_edges_are_the_metal_mesh_edges`, `the_pec_edges_are_written_with_direction_and_unit` |

## Not applicable

| Branch work | Reason |
| --- | --- |
| CSXCAD `WIP` viewer GUI (`6438a4f`..`f8e5f81`), `CSXCAD.Viewer` Python package, MATLAB `csxcad-view` | a separate Python/Qt viewer product; the Rust GUI is the egui `QCSXCAD`/`AppCSXCAD` port and already has its own viewer. The figure-tab/settings ideas are UI design input, not a port of existing Rust components |
| openEMS `WIP` Python `Results`, figures, `openems-view`, tutorial galleries (`9207285`..`9750c59`) | Python notebook/reporting surface for the viewer above |
| openEMS `WIP` `fba307d` (recreate ports and NF2FF boxes after `ReadFromXML`) | a setup-file mechanism that re-runs the Python port constructors; the Rust solver has no port objects because the XML already carries the geometry and excitations. Not applicable to the Rust architecture |
| `qtViewer`, `py_gui`, older `python` branches | obsolete experiments predating `master` |
| other `CI_testing` branches | CI configuration only |

## Deferred

| Branch work | What it would need |
| --- | --- |
| Python `Results`/figures | a reporting layer for the Python product; the Rust solver returns fields and probes through its own API |
| viewer GUI features (figure tabs, settings dock, item parts) | product scope for the egui viewer; tracked as GUI work, not an upstream port |

## Evidence

* Branch comparison: `git branch -r --list 'upstream/*'` and
  `git rev-list --count upstream/master..<branch>` in each submodule.
* Tests after the port: `cargo test` (workspace default members) is **865
  passed, 0 failed** across 36 test binaries; `csxcad-core` 166 lib and
  `openems-core` 271 lib among them. The Python bindings and the workspace
  `cargo check` are clean.
* `--debug-PEC` end to end, from
  `openems-cli 07_primitives.xml --no-simulation --debug-PEC`:

```text
[openEMS] PEC edges written to 'PEC_dump.vtp' (212 edges)
<Piece NumberOfPoints="108" NumberOfLines="212" ...>
<DataArray type="UInt8" Name="direction" ...> 0 0 ... 1 1 ... 2 2 ...
<FieldData><DataArray type="Float64" Name="LengthUnit" ...> 1 </DataArray></FieldData>
```

* `--debug-memory` output, from
  `cargo test -p openems-core the_memory_report -- --nocapture`:

```text
------- Stat: memory (operator built) -------
operator arrays (vv/vi/ii/iv) : 0.63 MiB
EC C/G/L/R coefficients       : 0.63 MiB
material grid                 : 1.56 MiB
field arrays (volt/curr)      : 0.31 MiB
total (arrays)                : 3.13 MiB (240.00 Byte/cell)
Peak memory (RSS)             : 12.42 MiB (952.47 Byte/cell)
-----------------------------------
```
