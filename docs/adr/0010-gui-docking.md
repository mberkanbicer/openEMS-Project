# ADR 0010: Drag-docking for the Rust GUI

**Status:** Implemented and accepted 2026-10-31 for this fork (tabs/splits; no floating panes)
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

## Decision

Adopted `egui_tiles 0.18` behind the `docking` feature in `qcsxcad-egui`. The
application enables it, so the three panes are a real tile tree; the fixed
panel path is kept for builds without the feature. The acceptance bar was:

1. the structure/inspector content renders unchanged (no duplicated widgets);
2. widths and the tile tree are persisted next to the window settings;
3. `Ctrl+B` / `Ctrl+I` still hide/show the corresponding panel;
4. keyboard tree navigation, the focus ring and the `Ctrl+K` palette keep
   working;
5. the existing 27 `qcsxcad-egui` + 17 `appcsxcad` tests pass, plus a new
   persistence round-trip test;
6. a 1440x900 capture shows the re-docked layout and is added to `audits/`.

All six points are met (2026-10-31): the pane contents are the existing widgets,
the tree and its visibility persist in `settings.json`, `Ctrl+B`/`Ctrl+I` use
`Tree::set_visible`, the tree keyboard/focus/palette tests pass, there are 32
`qcsxcad-egui` tests (4 docking) and 18 `appcsxcad` tests, and the default and
docked layouts are captured in `audits/gui-docking-1440.png` and
`audits/gui-docking-docked-1440.png`.

### Owner decision (2026-10-31)

The owner accepted the tab/split docking workflow as the docking scope for this
fork and does not require floating panes. The difference from the Qt application
is therefore a recorded scope decision, and `EXCEPTIONS.md` closes `E-013`
instead of keeping it open. Floating windows remain available as a future
change, but only through a new ADR and a separate viewport implementation.

## Consequences

- Approving it adds one GUI runtime dependency; it does not touch the solver,
  file formats or numerical results.
- Rejecting it leaves the current behaviour as the accepted parity level: panel
  sizes persist, panels toggle, but they cannot be dragged or floated. That
  difference must then be listed in `EXCEPTIONS.md` with this ADR as the
  decision record.
- Neither option changes the toolkit decision in ADR 0009 (egui/wgpu, all-Rust).
