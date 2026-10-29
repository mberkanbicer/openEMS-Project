# ADR 0009: GUI parity for AppCSXCAD (all-Rust)

**Status:** accepted 2026-10-29, revised 2026-10-29 (all-Rust requirement)
**Context:** RM-152, E-006, `docs/migration/audits/gui-parity.md`

## Context

ADR 0004 chose `egui` + `wgpu` and accepted a toolkit change. The owner
rejected that: the Rust application must match the native Qt Widgets
AppCSXCAD in design and usability. The owner also requires the result to stay
**all-Rust**.

The native application is Qt Widgets. `cxx-qt-lib` 0.10 exposes only
`qt_gui`, `qt_qml` and `qt_quickcontrols`; it has no `QWidget`/`QMainWindow`
bindings. A C++ Qt shell or a QML application would either leave C++ in the
product or change the widget model, so neither satisfies both constraints.

## Decision

Reproduce the native layout, palette and workflow in the existing **egui/wgpu**
application, all-Rust, and accept the residual differences that come from the
toolkit (fonts, widget metrics, native dialogs). The target layout is fixed by
`AppCSXCAD/qt-prototype/` and `audits/gui-qt-prototype.png`; the Rust
implementation is:

* light Fusion-like palette and a white viewport;
* `File`/`Info` menus and the native text toolbar (`New`, `Load`, `Save`,
  `Export`, `CollapseAll`, `ExpandAll`, `Material`, `Metal`, `Electrode`,
  `ProbeBox`, `ResBox`, `DumpBox`, `Box`, `MultiBox`, `Sphere`, `Cylinder`,
  `Polygon`, `User Defined`, `YZ`, `ZX`, `2D`, `3D`);
* the `Properties and Structures` dock with the `Properties / Primitives` and
  `Vis` columns;
* the `Rectilinear Grid` dock including the parameter list;
* the coordinate status bar and the supported view presets.

## Consequences

* No C++ GUI and no QML: the product stays all-Rust.
* Pixel identity with Qt is not claimed. The recorded limitation is the widget
  toolkit, not the workflow: creation, editing, visibility, undo, grid,
  parameters and exports all run through the Rust model.
* The Qt prototype remains as the layout reference only; it is not built or
  shipped.
* `RM-152` moves to `Implemented` when the workflow slice is reachable; the
  remaining parity items (dock split, `Vis` column placement, axis gizmo,
  native metrics) are listed in the audit.

## Alternatives rejected

* **Thin C++ Qt Widgets shell + Rust model via cxx**: exact widgets, but the
  owner requires all-Rust.
* **Qt Quick via cxx-qt**: all-Rust logic but QML, and not the Widgets model.
* **egui left as-is**: rejected by the owner; the design differed.
