# GUI modernization — Phase 0 audit

Status: baseline audit for the `Precision Workbench` redesign (DESIGN.md v1.0.0).
Date: 2026-10-30.
Scope: the all-Rust desktop GUI of QCSXCAD + AppCSXCAD (`QCSXCAD/rust-egui`,
`QCSXCAD/rust`, `AppCSXCAD/rust`). The numerical engine, file formats and
solver outputs are out of scope for presentation changes.

This audit is evidence for the redesign. Every statement below was read from the
code or observed in a captured frame; nothing is assumed from the Qt original.

## 1. Stack and version facts

| Item | Value | Evidence |
|---|---|---|
| UI toolkit | `egui` 0.37 (default fonts) | `QCSXCAD/rust-egui/Cargo.toml` |
| Window/input | `winit` 0.30, `egui-winit` 0.37 | same |
| 3D rendering | `wgpu` 30, `egui-wgpu` 0.37 | same |
| Docking | **none** — `egui` `Panel` layout only | no `egui_dock` dependency |
| Application framework | **none** — custom `winit` `ApplicationHandler` loop | `app.rs::run` |

There is no `eframe`, so persistence helpers (`eframe::Storage`) are not
available. Any layout/theme persistence must be implemented explicitly.

## 2. Architecture and data flow

```
AppCSXCAD (shell)                     QCSXCAD (library UI)            domain
┌───────────────────────────┐        ┌────────────────────────┐      ┌──────────────┐
│ menu / toolbar / dialogs  │ extra_ui│ EguiApp::build_ui      │      │ Document     │
│ AppAction queue ──────────┼───────► │  status bar (bottom)   │ ───► │ Structure    │
│ shortcuts                 │        │  tree (left)           │      │ Grid         │
│ project I/O, exports      │        │  inspector (right)     │ ◄─── │ undo/redo    │
└───────────────────────────┘        │  viewport (central)    │      └──────────────┘
                                     │  WgpuRenderer + Camera │
                                     └────────────────────────┘
```

- `EguiApp::build_ui` owns the panel layout. The embedding application draws its
  menu, toolbar, dialogs and error strip through the `extra_ui` callback before
  the QCSXCAD panels.
- The viewport is the wgpu surface itself, painted *under* egui; the central
  panel has `Frame::NONE` and only provides the picking surface, axis gizmo and
  overlays. This is why no viewport texture or image widget exists.
- Geometry is rebuilt only when `document.revision()` changes
  (`render()` → `last_geometry_revision`). Camera changes never rebuild geometry.
  3D is redrawn on demand (`request_redraw`), not on a continuous timer.
- Selection lives in `GuiState::selection` (property IDs + primitive IDs) and is
  synchronised tree ↔ viewport ↔ inspector by shared IDs (`PropertyId`,
  `PrimitiveId`).
- Model mutation goes through `Document` operations (`move_primitive_by`,
  `apply_property_edit`, …); the UI never edits fields directly. Undo/redo is
  document-level, and a drag is one gesture (`begin_gesture`).
- Long operations (load/save/export) run after the frame through `AppAction`, so
  the UI callback never performs blocking I/O.

## 3. Screen inventory (current)

| Region | Contents | State |
|---|---|---|
| Menu bar | File (New, Load, Save, Save As, Export ▸, Exit), Info ▸ About | wired |
| Command strip | file actions, collapse/expand, 6 property types, 6 primitive types, 4 view presets, 3 transform modes | wired, but wider than 1920 px |
| Left dock | tree (properties/primitives, expand, visibility), rectilinear grid, parameters | wired |
| Viewport | 3D structure, axis gizmo, hover label, navigation hint | wired |
| Right dock | property editor, primitive editor, transform editor | wired, contextual |
| Status bar | cursor coordinates, selection, property/primitive counts | wired |
| Dialogs | load, save-as, 6 exports, about, delete confirmation | wired |
| Error strip | bottom panel, only when an error exists | wired |

## 4. Command inventory and applicability

All commands below are reachable and wired; “disabled” means the control is
shown disabled with a stated reason, never silently inert.

| Command | Shortcut | Preconditions | Handler |
|---|---|---|---|
| New | Ctrl+N | edit mode | `AppAction::New` |
| Load | Ctrl+O | — | `Dialog::Load` |
| Save | Ctrl+S | document + path | `AppAction::Save` |
| Save As | Ctrl+Shift+S | edit mode | `Dialog::SaveAs` |
| Export XML / VTK / STL / PLY / POV / X3D / PNG | — | depends on format | `AppAction::Export*` |
| Exit | — | — | `AppAction::Exit` |
| Undo / Redo | Ctrl+Z / Ctrl+Shift+Z, Ctrl+Y | document | `Document::undo/redo` |
| Delete | Del | selection, no text focus | tree confirmation |
| Expand / collapse all | — | document | `EguiApp::expand_all` |
| Add property (6 types) | — | document | `AppAction::AddProperty` |
| Add primitive (6 types) | — | document | `AppAction::AddPrimitive` |
| View presets (YZ, ZX, 2D, 3D) | — | — | `EguiApp::set_view_dir` |
| Parallel projection | — | — | `EguiApp::set_parallel_projection` |
| Transform mode (move/rotate/scale) | — | — | `EguiApp::set_transform_mode` |
| Orbit / zoom / pan-drag | MMB drag / wheel / left drag | pointer over viewport (after this audit's fix) | `handle_navigation`, viewport drag |
| Pick | click | document | `pick_primitive` |
| Visibility toggle | — | property | `PropertyEdit::Visible` |

## 5. Findings (ranked)

1. **Toolbar overflow.** The command strip is wider than a 1920 px logical
   window; the view presets and transform modes are cut off behind a horizontal
   scroll area. This hides primary commands.
2. **Navigation leaks outside the viewport.** `handle_navigation` zooms on every
   wheel event and starts orbiting on every middle press, regardless of pointer
   position. Scrolling the tree therefore zooms the 3D view, and a middle-drag
   over an editor rotates the model.
3. **One theme only, no fallback.** `build_ui` sets `Visuals::light`; the palette
   constants are ad hoc and there is no dark or high-contrast mode. DESIGN.md
   requires dark as the recommended default.
4. **No Fit All / Fit Selection.** The camera fits exactly once
   (`auto_fit`); after orbiting there is no way to recover the framing except by
   restarting.
5. **Status bar carries no units, tool or projection fact.** It shows
   coordinates in drawing units but never names the unit, the active tool, the
   projection mode or whether a document is modified.
6. **No panel visibility control.** Both docks are always present; there is no
   keyboard/menu fallback for hiding them (DESIGN.md §2 requires one).
7. **Keyboard access is partial.** Delete and the file shortcuts exist; the tree
   is not arrow-navigable, and focus is not visibly distinct from selection.
8. **No command search.** There is no `Ctrl+K` registry, so rare exports are only
   discoverable through menus.
9. **No docking.** Panels are fixed left/right/bottom. This is accepted for
   Phase 2 only if panel sizes persist and can be toggled; true drag-docking is
   deferred until an ADR approves a docking crate compatible with egui 0.37.
10. **Screenshot pipeline defect (not a product defect).** Early captures missed
    the status bar because a non-DPI-aware capture grabbed a background window;
    the status bar is present and verified. The helper now sets DPI awareness and
    forces the app topmost.

## 6. Baseline evidence

- `docs/migration/audits/gui-demo.png` — 2578×1398 physical capture of the
  maximized window (`ppp` 1.25) with the status bar visible.
- Headless UI probes confirm: the bottom panel reserves 24 logical px, its paint
  job is emitted with clip `[[0, 979.8] – [1920, 1008.8]]` for a 1008.8 pt screen,
  and the status strip is painted before the side panels.
- `cargo test -p qcsxcad-egui -p appcsxcad -p qcsxcad-core`: 82 tests green
  (17 + 13 + 52) at the baseline.

## 7. UI ↔ domain boundary (must not move)

- `GuiState` (view mode, selection, projection, view direction) is presentation
  state; it must never be serialized into a project file.
- `Document` is the only mutation surface; `ProjectFile` is the only file I/O
  surface. Presentation refactors must not touch either.
- Units: the grid carries `delta_unit`; coordinates displayed in the status bar
  are divided by it, matching the native read-out. A unit label must be derived
  from the same value, never hardcoded.
- Rendering colours come from property data (fill/edge/alpha). The viewport
  background is presentation state and may follow the theme.

## 8. Redesign phases and acceptance

| Phase | Deliverable | Acceptance |
|---|---|---|
| 0 | this audit | evidence above, no code change |
| 1 | tokens, dark/light/high-contrast themes, shell, status bar, toolbar fit, keyboard/menu fallbacks | builds; theme tests; strip fits 1280/1440/1920; screenshots |
| 2 | resizable + persisted panel sizes, panel toggles, selection-sync regression test | layout survives restart; tree↔viewport↔inspector test |
| 3 | fit all/selection, projection + view state read-out, navigation confined to the viewport | camera tests; wheel over tree does not zoom |
| 4 | status/inspector units, validation messages, export affordances | unit tests on formatting; no fabricated states |
| 5 | full validation run, screenshots, migration records | `cargo test` workspace + acceptance script + updated register |

Phase 1 is implemented in this change; later phases remain tracked in
`REMEDIATION_TASKS.md` with their own verification rows.

## 9. Phase 1 implementation and evidence (2026-10-30)

Implemented in this change:

- `theme.rs`: semantic palettes for dark (default), light and high contrast,
  one spacing/type scale, and a linearised viewport clear colour. Contrast is
  asserted for body text, tertiary text and selected rows on every palette.
- Shell: `File`/`Edit`/`View`/`Info`; grouped command strip that wraps whole
  groups at 1280 px and fits one row at 1440/1920 px; `+ Property` /
  `+ Primitive` menus replace twelve toolbar buttons; panel toggles with
  Ctrl+B / Ctrl+I; theme persisted in `settings.json`.
- Status bar: coordinates and drawing unit (`mm` on the fixture), active tool,
  selection summary, projection, property/primitive counts, unsaved marker.
- Viewport: navigation (wheel, middle-drag) is ignored outside the viewport;
  `Fit All` uses the uploaded bounds and `Fit Selection` merges the selected
  primitives' model bounding boxes; the axis triad uses theme colours.
- Docks: fixed 320/360 px defaults, the tree is bounded so the grid and
  parameter sections stay reachable at 800 px height, and the duplicate inner
  headings were removed.

Verification:

- `cargo test -p qcsxcad-core -p qcsxcad-egui -p appcsxcad`: 52 + 24 + 13 pass.
- Screenshots: `gui-dark-1280.png` (two-row strip, no clipped command),
  `gui-dark-1440.png`, `gui-dark-1920.png`, `gui-light-1440.png`,
  `gui-high-contrast-1440.png`, and `gui-selection-1440.png` (a real click on
  the tree fills the inspector and the status bar).
- The status bar defect in the first captures was a capture-pipeline artifact
  (a non-DPI-aware grab of an occluded window), not a product defect; the
  helper now sets DPI awareness, forces the app topmost and captures the client
  rectangle.

Recorded finding (not changed in this phase): the wgpu surface is an sRGB
target while the renderer writes stored material colours as linear values, so
materials render lighter than in the native Qt application. Changing it alters
the appearance of every property and belongs to a renderer colour-management
change with its own validation.

Remaining phases: persisted dock sizes (egui panel state is session-only),
arrow-key tree navigation and visible focus rings, a `Ctrl+K` command registry,
and a colour-managed viewport.
