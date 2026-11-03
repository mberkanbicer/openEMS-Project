# Desktop workbench audit

## Scope of the desktop product

`AppCSXCAD` is the **geometry and structure editor**, matching the native
product's role: models are created, edited and exported, and simulation runs
through the CLI, Python or Octave. The GUI does not embed the FDTD solver and
never claims to. "Run simulation in the GUI" is therefore
`INTENTIONALLY_UNSUPPORTED` (native scope), not a missing port feature.

## Current implementation (Phase 0/1 audit)

Full audit: `docs/migration/audits/gui-modernization-audit.md`. Summary:

| Area | State |
|---|---|
| Framework | egui 0.37, wgpu 30, winit 0.30; no docking crate; custom event loop |
| Shell | Menu `File/Edit/View/Info`, grouped command strip (wraps whole groups at 1280 px), theme menu, panel toggles (Ctrl+B/Ctrl+I) |
| Docks | Structure (tree, bounded, grid, parameters) and Inspector (property/primitive/transform), 320/360 px, resizable |
| Viewport | wgpu 3D under egui, picking, hover label, drag move/rotate/scale, orbit/zoom confined to the viewport, Fit All/Selection, axis triad |
| Status bar | coordinates + drawing unit, active tool, selection, projection, counts, unsaved marker |
| Themes | dark (default), light, high contrast; WCAG-checked; persisted in `settings.json` |
| Project | XML load/save, undo/redo, exports (XML/VTK/STL/PLY/POV/X3D/PNG) |
| Tests | 52 `qcsxcad-core`, 24 `qcsxcad-egui`, 13 `appcsxcad` |

## Verified interaction path

`docs/migration/audits/gui-selection-1440.png` is a real click: the tree row is
selected, the inspector fills with the material/box fields, and the status bar
shows the selection. The GUI is built and launched on this Windows host.

## Gaps

- Material colours render lighter than native (sRGB vertex colours); `GUI-001`.
- Panel sizes/layout are session-only; `GUI-002`.
- No keyboard arrow navigation in the tree, no visible focus ring audit.
- No command palette (`Ctrl+K`).
- Docking is deferred until an egui-0.37-compatible crate is approved (ADR).
- No simulation job panel (out of native scope).

## Gate 8 assessment

The editor workflow is usable and tested; it does not execute simulations, so
the full "edit → mesh → solve → inspect" loop is split across the editor and the
CLI/Python/Octave tools by design. No result-plot surface exists because the
desktop product does not own results.
