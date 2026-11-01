# ADR 0012: optional GPU acceleration (supersedes ADR 0002 scope note)

**Status:** Stages 1-2 implemented 2026-11-01 (`gpu` feature: wgpu device, buffer round-trip and the Yee E/H update kernels, validated against the CPU formula at 6e-8); engine integration pending
**Decision owner:** Project owner
**Related:** ADR 0002, component matrix "GPU compute"

## Context

ADR 0002 excluded GPU compute from the port. The owner now asks for a GPU
backend. The solver's inner loops are the E/H field updates over the Yee grid;
openEMS stores fields as `FDTD_FLOAT` (f32), which matches GPU compute well.
The GUI already depends on `wgpu`, so the runtime and adapter code are present
in the workspace.

## Decision

Add an **optional** `gpu` feature to `openems-core` that runs the field-update
kernels on a `wgpu` compute device. The CPU engine stays the reference and the
default; the GPU path must produce the same physics within a justified f32
tolerance and fall back to the CPU when no adapter is available.

## Scope and phases

1. **Device layer** — `GpuContext` (adapter/device/queue), buffer layout equal
   to `ArrayNIJK<f32>` (component-major), readback, deterministic error
   reporting; feature-gated and excluded from the default build.
2. **Update kernels** — E-field and H-field updates with the existing `vv`,
   `vi`, `ii`, `iv` coefficients; PML auxiliary fields are CPU-side in phase 1.
3. **Step orchestration** — one GPU dispatch per update, staging coefficients
   once; sync only where extensions need host data. Avoid per-step allocations.
4. **Extensions** — PML, Mur, dispersive, excitation and ports remain CPU-side
   until each has a GPU kernel and a differential test; a model that uses an
   unsupported extension on GPU must fall back explicitly, not silently.
5. **Validation** — cavity, MSL notch and Coax cases against the CPU engine:
   probe traces and S-parameters within an f32 bound derived from the CPU f32
   variance; bitwise equality is not expected.
6. **Performance** — wall time and peak RSS vs the CPU engine on the recorded
   three cases; a GPU result is reported only with hardware and driver named.

## Acceptance

- Default build unchanged; `gpu` is additive and documented.
- A GPU run reproduces the CPU results within the recorded bound on at least
  the three benchmark cases, or the feature reports why it cannot.
- No extension silently runs CPU physics while claiming GPU acceleration.
- CI without a GPU skips the GPU suite with an explicit message.

## Risks

- Adapter availability in CI and WSL2; the local GUI machine has a wgpu adapter,
  CI does not.
- f32 reduction order changes the last bits; the bound must be measured, not
  guessed.
- Kernel coverage (PML/dispersive/ports) is the long pole; phase 1 is core
  updates only.
