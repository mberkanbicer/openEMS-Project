# QCSXCAD and AppCSXCAD GUI Audit

**Status:** Source workflow map complete; the later WSL root build compiled
and linked the GUI components, but manual interaction remains unvalidated in
the headless environment. No GUI or submodule source was changed.

## Architecture and model boundary

`QCSXCAD` is both a `QMainWindow` and a `ContinuousStructure`. It edits the
CSXCAD model directly, exposes XML read/write, and composes the `QCSTreeWidget`,
`QCSGridEditor`, parameter editor, and `QVTKStructure` renderer. Qt signals
connect tree, grid, parameter, and rendering updates. `AppCSXCAD` is the
desktop wrapper; it adds menus, file tracking, settings, and command-line
exports.

The property/structure tree groups primitives under properties. It supports
selection, property visibility toggles, expand/collapse, context-menu
creation, editing, copying, and deletion. Geometry editors cover box,
multi-box, sphere, cylinder, cylindrical shell, polygon, and user-defined
primitive forms (other primitive types fall back to a generic editor).
Property editing has specialized widgets for material, excitation, probe,
dump, and resolution-box properties, plus generic name/color controls.
Property creation includes material, metal, excitation, probe, resolution, and
dump properties. The grid editor supports axis line entry, length units,
homogeneous/inhomogeneous discretization, resolution increase, edge detection,
grid-plane selection, and grid opacity.

## Rendering, navigation, and export

`QVTKStructure` embeds the VTK Qt widget, draws axes and grid planes, maps
CSXCAD primitive geometry/transforms to VTK actors, and optionally draws
discrete-material models. The viewer supports 2D orthographic plane views,
3D interaction, parallel projection, best-fit, and image capture. Exports
include CSXCAD XML, POV-Ray, X3D, per-visible-property VTK PolyData/STL/PLY,
and a 3D-view PNG. PNG export in 2D is explicitly unsupported. Property
mesh exports use the grid delta unit as their scale.

## Project I/O and application behavior

`ReadFile` accepts a CSXCAD XML document or an openEMS XML document and reads
the openEMS boundary-condition attributes before locating the embedded
`ContinuousStructure`. The loaded structure is passed to the CSXCAD XML
reader, then the tree/grid/view are refreshed. XML export serializes the
`ContinuousStructure` model. Read/validation failures are generally shown as
Qt warning dialogs; `ReadFile` reports `false` for a missing file or absent
root, but returns `true` after a parser warning if a root was found.

The application has New, Load, Save, Save As, and export menu actions.
`Save` writes to the filename most recently set by `ReadFile`; the menu's
Save-As action calls the general export dialog, which does not update that
filename. Window geometry is persisted through `QSettings`; window state
restoration is currently commented out. Edit mode gates creation/editing and
some file actions; view mode retains inspection and export actions.

## Dependencies, build, and tests

Both components use C++11 and CMake. QCSXCAD requires CSXCAD, TinyXML, VTK,
and Qt; AppCSXCAD additionally requires HDF5 and links the installed
QCSXCAD/CSXCAD libraries. Qt4/5/6 selection is conditional on VTK's Qt
metadata, with a Qt4/5 guess for older VTK. VTK 8 and VTK 9+ use different
Qt widget classes. Unix builds enable PIC/RPATH and install a shell launcher;
the Linux application startup sets `LC_NUMERIC=C`. The Windows package flow
uses vcpkg and packages the Qt plugins/runtime DLLs. AppCSXCAD's checked-in
`.bat` launcher still contains machine-specific legacy paths.

Neither CMake project registers tests (`enable_testing`, `add_test`, QtTest,
or another test framework were not found). No manual GUI checklist or
automated interaction suite is present in these submodules. Root CI contains
GUI build/package jobs on selected platforms and uses `--disable-GUI` on
some headless Linux configurations; this is build coverage, not UI behavior
coverage. The Qt/VTK GUI could not be launched here, so file dialogs,
editing/rendering/export interactions and platform-specific plugin behavior
have no runtime validation. A Windows CMake configure attempt identified
missing `CSXCAD` library/include paths and TinyXML library/include files before
reaching the Qt/VTK discovery steps; no GUI target was built.

## Source findings and reference questions

- **Confirmed source defect — discrete-material/render setting aliases edit
  mode.** `QCSXCAD_Global::SetRenderDiscMaterial` writes `m_EnableEdit`, and
  `GetRenderDiscMaterial` reads that same field; the declared
  `m_RenderDiscMat` is not used. `--RenderDiscMaterial` therefore does not
  control rendering independently and can change edit-mode state depending on
  command-line option order. Preserve the observed behavior only if explicitly
  required; otherwise resolve with the upstream component before migration.
- **Confirmed source defect — grid-plane labels use the X slider index.**
  `QCSGridEditor::Update` passes `m_PlanePos[0]->value()` to X, Y, and Z label
  updates. When slider positions differ, the Y/Z labels can describe a
  different plane than their sliders; unequal grid dimensions also make the
  reused index potentially invalid. No GUI run was available to observe the
  resulting VTK/model behavior.
- **Save-As semantics require a reference decision.** Save As writes through
  the general XML export dialog but leaves `AppCSXCAD::m_filename` unchanged,
  so subsequent Save continues targeting the previous filename (or an empty
  path for a newly created model). There is no UI test for this sequence.
- **Nested XML search requires a reference case.** `FindRootNode` begins from
  the first child but advances with `node->NextSiblingElement()` inside the
  child loop; this appears to skip later child siblings. Test XML with the
  `ContinuousStructure` nested under a non-first sibling before determining
  compatibility impact.
- **OpenEMS wrapper preservation is not established.** The GUI reads
  boundary-condition attributes from an openEMS wrapper, but its public
  `Write2XML` delegates to `ContinuousStructure`; verify whether saving an
  opened solver project is expected to preserve solver settings or only the
  embedded geometry.

## Migration contracts

The Rust design must decide whether to preserve the QCSXCAD library boundary
separately from the AppCSXCAD executable, the direct mutable
`ContinuousStructure` model integration, XML/openEMS-wrapper import behavior,
property and primitive editor coverage, grid editing, visibility and camera
controls, VTK-backed exports, view-only mode, and the Qt/VTK platform matrix.
The two confirmed source defects and the open compatibility questions above
must be resolved against a reference build before they become normative Rust
behavior.

## Migration decisions (2026-10-27)

- **Save keeps the openEMS wrapper.** Native `QCSXCAD::Write2XML` delegates to
  `ContinuousStructure::Write2XML`, so saving an opened solver project writes
  only the geometry and silently drops `<FDTD>`, `<BoundaryCond>` and the
  excitation settings. `qcsxcad_core::ProjectFile` remembers the loaded
  document and replaces only its `<ContinuousStructure>` element. This is a
  deliberate deviation, chosen because the native behavior is data loss.
- **Save As adopts the new path.** Native `ExportGeometry` (the Save-As action)
  writes the chosen file but leaves `AppCSXCAD::m_filename` unchanged. The port
  updates the path so a following Save targets the file the user just chose.
- **No random fill colors.** Native assigns `rand()%256` colors in the
  `CSProperties` constructor. The port leaves the color unset until the user
  picks one, keeping documents and exports reproducible.
- **Property file names are sanitized.** Native names each exported file after
  the property; an empty or unsafe name now falls back to `property_<index>`
  and replaces path separators.
- **In-app path dialogs.** `QFileDialog` is replaced by a path window (the
  dialog is the OS integration, not the file operation); the operations
  themselves are covered by unit tests.
- **`--RenderDiscMaterial` no longer toggles edit mode.** The confirmed native
  defect is not reproduced: the render flag and the edit flag stay separate.
  Discrete-material rendering is not ported yet and is tracked as RM-147.
