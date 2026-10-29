# ADR 0009: Qt Widgets GUI parity for AppCSXCAD

**Status:** accepted 2026-10-29 (supersedes the toolkit part of ADR 0004)
**Context:** RM-152, E-006, `docs/migration/audits/gui-parity.md`

## Context

ADR 0004 chose `egui` + `wgpu` for the GUI and accepted a toolkit change. The
owner has rejected that trade-off: the Rust application must match the native
Qt Widgets AppCSXCAD in design and usability, not merely in function.

The native application is Qt Widgets (`QMainWindow`, `QMenuBar`, `QToolBar`,
`QDockWidget`, `QTreeWidget`, a VTK viewport). `cxx-qt` is the natural
Rust/Qt bridge, but `cxx-qt-lib` 0.10 exposes only `qt_gui`, `qt_qml` and
`qt_quickcontrols`; it has no `QWidget`/`QMainWindow` bindings. A Qt Quick
application via `cxx-qt` would be all-Rust but would not reproduce the Widgets
layout, metrics or interaction model.

## Decision

Build the parity GUI as a **thin Qt Widgets front-end in C++ over the Rust
model**, bridged with `cxx`. The C++ layer owns only the widget tree and the
event wiring; the structure, materials, grid, operators, engine and file I/O
stay in `csxcad-core`/`openems-core`.

The layout prototype in `AppCSXCAD/qt-prototype/` fixes the target: menus
`File`/`Info`, the text object toolbar, the `Properties and Structures` dock
with the `Properties / Primitives` and `Vis` columns, the `Rectilinear Grid`
dock, the `Parameter` dock and the coordinate status bar
(`audits/gui-qt-prototype.png`).

## Consequences

* The GUI shell is C++. This narrows ADR 0008: no C++ API surface is exposed
  for the solver, but the GUI front-end is accepted as C++ code driven by the
  Rust model.
* The build gains a Qt6 Widgets target next to the Rust workspace. It is built
  only when the GUI is requested, so headless/server builds do not need Qt.
* The egui application remains until the Qt shell reaches feature parity, then
  it is retired.
* `RM-152` stays `Analyzed` until the shell loads and edits a real structure
  through the bridge; the prototype alone is not the migration.

## Alternatives rejected

* **Qt Quick via cxx-qt**: all-Rust, but not the Widgets layout; cannot meet
  "birebir".
* **ritual / generated QWidget bindings**: no maintained QWidget binding set
  for Qt6; the build risk is higher than the thin shell.
* **egui restyle**: explicitly rejected by the owner; it cannot be
  pixel-identical.
