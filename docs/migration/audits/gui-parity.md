# GUI parity audit (E-006)

**Date:** 2026-10-29
**Question:** does the Rust GUI match the native QCSXCAD/AppCSXCAD in design and
usability?

**Answer: no.** E-006 recorded the missing native side-by-side comparison. This
audit records the larger fact behind it: the current GUI is an **egui/wgpu**
application (ADR 0004, D-04), so it is a different toolkit with a different
layout, theme and interaction model. It is not a visual near-match that a
side-by-side would confirm; the design is different.

## Reference

| Native AppCSXCAD (Qt Widgets, `doc-src/concepts/images/appcsxcad.png`) | Rust port (`audits/gui-windows.png`) |
| --- | --- |
| Light Qt theme, native menu and toolbar metrics | Dark egui theme, custom top bar |
| `File`, `Info` menus | `File`, `Info` menus (different contents) |
| Text toolbar: `homo`, `inhomo`, `increase Disc`, `detect edges`, `CollapseAll`, `ExpandAll`, `Material`, `Metal`, `Electrode`, `ProbeBox`, `ResBox`, `DumpBox`, `Box`, `MultiBox`, `Sphere`, `Cylinder`, `Polygon`, `User Defined`, `YZ`, `ZX`, `2D`, `3D` | No object/view toolbar; a `QCSXCAD 5 properties / 5 primitives` strip and `Undo`/`Redo`/`+ Property`/`Delete` |
| Dock **Properties and Structures** with the columns `Properties / Primitives` and `Vis` | Tree with native row labels but no column headers and a different row metric |
| Dock **Rectilinear Grid**: X/Y/Z `Min`/`Max Lines`, `Edit`, `Drawing unit [m]`, `Grid opacity` | Absent; grid editing is a separate panel |
| Dock **Parameter**: list plus `New` | Absent as a dock |
| Status bar with live `X:`/`Y:` coordinates | Absent |
| Viewport with X/Y axis gizmo and `YZ`/`ZX`/`2D`/`3D` presets | Viewport with orbit camera, no axis gizmo or presets |
| Property/primitive editors in-place in the tree flow | Editors in a side panel |

The functional model is ported (tree labels, editors, undo, exports, renderer),
but "birebir aynı tasarım ve kullanışlılık" is not met.

## Why it happened

D-04 chose `egui` + `wgpu` over Qt bindings and accepted the toolkit change as a
design decision. The migration then verified the model, the renderer and the
exporters, not visual parity. The user now requires parity, which reopens D-04.

## Options

| Option | What it means | Effort | Keeps all-Rust | Risk |
| --- | --- | --- | --- | --- |
| **A. Qt Widgets in Rust (cxx-qt)** | Port `AppCSXCAD.cpp`/`QCSXCAD` to Rust Qt Widgets, mirror the menus, toolbar, docks, tree columns, grid/parameter panels and status bar; embed the existing wgpu view in a `QWidget`/`QWindow` container | 4-8 weeks | yes | Qt5/6 dev dependency in the Rust build; wgpu-in-Qt surface handling; the largest single work item left |
| **B. Native Qt GUI + Rust core via C ABI** | Keep the native Qt AppCSXCAD front-end (exact UI) and drive the Rust structure/operator/engine through a reviewed C ABI | 1-2 weeks | no (a C++ GUI remains) | Reopens D-08 (no C++ compatibility surface); the C ABI grows |
| **C. egui restyle to the Qt layout** | Light theme, text toolbar, left docks for Properties/Grid/Parameter, tree column headers, status bar, axis gizmo and view presets | 1-2 weeks | yes | Close in layout and workflow, never pixel-identical (fonts, metrics, native widgets) |

## Recommendation

If "birebir" is literal, only **B** delivers it in a reasonable time; **A** is
the only path that is both literal and all-Rust. **C** is the cheapest way to
close most of the usability gap but cannot claim identity.

The work should not start before this choice is recorded as a new ADR that
supersedes D-04 (and, for B, D-08).
