# ADR 0010: Drag-docking for the Rust GUI

**Status:** Proposed — owner decision required
**Date:** 2026-10-30
**Context:** RM-176, `audits/gui-modernization-audit.md` §2/§9, ADR 0009
**Decision owner:** Project owner

## Context

The all-Rust AppCSXCAD shell reproduces the native Qt layout with two fixed
docks (`Structure`, `Inspector`), a toolbar and a status bar. Panel widths are
persisted (`RM-173`) and both docks can be toggled from the View menu or with
`Ctrl+B` / `Ctrl+I`, which is what the Phase-2 audit accepted.

The native Qt application also allows panels to be dragged, floated and
re-docked. The Rust shell does not. The audit deferred that until a docking
crate compatible with `egui 0.37` was identified, because `egui` panel state is
otherwise session-only.

## Evidence (checked 2026-10-30)

| Crate | Latest | `egui` requirement | Verdict |
|---|---|---|---|
| `egui_dock` | 0.21.1 | `0.36` | not compatible with the workspace `egui 0.37` |
| `egui_tiles` | 0.18.0 | `0.37.0` | compatible |

`egui_tiles` 0.18.0 is MIT OR Apache-2.0, declares `rust-version 1.95.0`, and
provides a tiling layout with drag/re-dock and resizing. It does not provide
floating windows; Qt-style floating panels would still need a separate viewport
implementation.

## Decision (proposed)

Adopt `egui_tiles 0.18` behind a feature flag in `qcsxcad-egui`, use it for the
two existing docks only, and keep the current fixed-panel code path as the
default until the tiling layout passes the same evidence bar:

1. the structure/inspector content renders unchanged (no duplicated widgets);
2. widths and the tile tree are persisted next to the window settings;
3. `Ctrl+B` / `Ctrl+I` still hide/show the corresponding panel;
4. keyboard tree navigation, the focus ring and the `Ctrl+K` palette keep
   working;
5. the existing 27 `qcsxcad-egui` + 17 `appcsxcad` tests pass, plus a new
   persistence round-trip test;
6. a 1440x900 capture shows the re-docked layout and is added to `audits/`.

Until the owner approves the dependency, the product keeps the verified
persisted-panel behaviour and this remains the only open GUI parity item.

## Consequences

- Approving it adds one GUI runtime dependency; it does not touch the solver,
  file formats or numerical results.
- Rejecting it leaves the current behaviour as the accepted parity level: panel
  sizes persist, panels toggle, but they cannot be dragged or floated. That
  difference must then be listed in `EXCEPTIONS.md` with this ADR as the
  decision record.
- Neither option changes the toolkit decision in ADR 0009 (egui/wgpu, all-Rust).
