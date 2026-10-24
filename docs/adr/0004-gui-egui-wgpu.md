# ADR 0004 - egui/wgpu for the GUI

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-04, RM-097..RM-106

## Context

QCSXCAD and AppCSXCAD are Qt/VTK applications. A faithful Rust port needs a
renderer for geometry, mesh and field data, plus desktop integration. A Qt
binding would keep the C++ dependency the migration is removing; a web frontend
would change the deployment model.

## Decision

Use `egui` + `winit` + `wgpu` for the Rust GUI crates (`qcsxcad-egui`,
`appcsxcad`). Keep the user-facing workflows and the CSXCAD model as the source
of truth.

## Consequences

- The GUI is native and GPU-accelerated without Qt/VTK.
- Export paths (VTK/STL/PLY/POV/X3D) must be implemented in Rust rather than
  delegated to VTK (RM-104).
- Interactive parity with the native applications still needs the manual QA
  checklist (RM-106).
