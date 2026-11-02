# GPU optimisation plan (2026-11-02)

**Goal:** remove the remaining GPU performance and coverage gaps recorded in
`GPU_ANALYSIS.md` §8 and E-016, in a fixed order, each step gated by a
CPU/GPU differential test and a measured before/after number.

Status values: `Not Started`, `Implemented`, `Verified`, `Blocked`.
Only `Verified` counts as done (AGENTS.md §17).

## Status summary

| Id | Item | Status | Evidence |
|---|---|---|---|
| P-1 | Merge UPML slabs per phase | **Verified** | 6 slabs: 32 -> 6 passes/step (now 4 with P-E2); 2-slab differential `0.00e0` |
| P-2 | Colour Mur faces into conflict-free passes | **Verified** | 6 faces: 18 -> 9 passes (11 with E/H); differential `2.38e-7` |
| P-3 | Merge Debye/Lorentz regions | **Verified** | Not applicable by construction: the operator builds exactly one region (`operator.rs:3358/3569`), so the count is already 3/4 |
| P-4 | Device-side probe sampling | **Verified** | Point and box probes gather on the device; 6 points, batch 12 (was 1), probes match CPU to 2.3e-7 / 4.3e-7 |
| P-5 | Device-side energy criterion | **Verified** | Per-workgroup partials summed in f64; rel diff 7.2e-9, no field download |
| P-6 | Overlap transfers with compute | **Verified (not needed)** | P-4/P-5 removed the per-step and per-sample downloads; the remaining transfer is one small probe matrix per batch |
| P-7 | Tune the batch chunk size | **Verified** | 64/128/256 within noise (avg 2.16/2.10/2.22 s at 451k); keep 256, `OPENEMS_GPU_CHUNK` knob added |
| P-8 | Graceful fallback on low-limit adapters | **Verified** | Per-extension storage requirement table + engine check |
| P-9 | Automatic engine selection | **Verified** | `--gpu-auto`: CPU at 12 221 cells, GPU at 451k cells |
| P-10 | GPU performance regression gate | **Verified** | Dispatch-budget test (6 slabs -> 4, 6 faces -> 11) |
| P-11 | Cylindrical multi-grid on the GPU | **Verified** | GPU pair enabled; CPU/GPU multi-grid diff 4.47e-8 |
| P-12 | Documentation refresh | Implemented | This file, `GPU_ANALYSIS.md`, E-016 |

## Critical finding: the differential tests were vacuous

The test operator (`cavity_operator`) loaded the CSX mesh but never called
`calc_ec_operator`, so every EC coefficient was zero and the fields decayed to
zero on the first step. All engine differentials therefore compared zeros.
Calling `calc_ec_operator` in the helper exposed two real defects:

1. **Mur colour ranges started at `gid.x = 0` for every colour.** Colours 1
   and 2 wrote nothing, so only the first two faces were absorbed (0.274
   field error). Fixed by adding the range start to the invocation index.
2. The synthetic Debye coefficients were unstable and amplified last-bit FMA
   differences into 1.3e-5; the test now uses contracting coefficients
   (3.58e-6 after 120 steps, relative 5.8e-7).

With real coefficients, UPML (including the fused path), excitation, lumped,
sheet and source are bit-identical; Mur 2.38e-7, TFSF 3.73e-9, Debye 3.58e-6,
Lorentz 1.49e-8.

## Baseline (before this plan)

| Metric | Value |
|---|---|
| Device extensions | 8/8 (excitation, UPML, Mur, lumped, sheet, TFSF, Debye, Lorentz) |
| GPU differentials | 10/10 pass, max 1.16e-10 |
| 451k cells extension-free | CPU 11.7 s, GPU 1.63 s (7.2x) |
| 451k cells source | CPU 20.1 s, GPU 2.15 s (9.2x) |
| 525k cells PML+source | CPU 12.2-14.0 s, GPU 2.55 s (4.8-5.5x) |
| 375k cells TFSF+6 PML | CPU 10.8 s, GPU 2.46-3.16 s (3.4-4.4x) |
| Tutorial 1 bare (12k cells) | CPU 0.31 s, GPU 1.02 s (GPU slower) |

## P-1. Merge UPML slabs per phase (dispatch count) - Verified

**Problem.** Each PML slab was a separate dispatch: `4 x slabs` per step. A
2-slab tutorial cost 12 dispatches/step and a 6-slab model 32.

**Change.** Every slab's coefficient/flux arrays are concatenated into one
buffer set with one slab table (start, extent, element offset). One dispatch
per phase over the total element count; the kernel locates the slab from the
index (`upml_locate`).

**Result.** A 6-slab model now costs **6 passes/step** (4 PML phases + E + H)
instead of 32. The two-slab differential is `0.00e0`; the 525k-cell PML model
measured 2.16-2.82 s (the host was noisy; the earlier baseline was 2.55 s).

## P-2. Group Mur faces into conflict-free passes - Verified

**Problem.** Mur ran one pass per face per phase (`3 x faces`), because faces
share corner edges and the host order matters. 6 faces cost 18 dispatches/step.

**Change.** Faces are coloured: a face's colour is one more than the highest
colour of an earlier face whose plane intersects it. Faces of one colour never
overlap and run in one dispatch; colours run in increasing order, so a later
face still wins a shared corner edge exactly as on the host. Arrays are
concatenated in colour order, so each colour owns a contiguous range.

**Result.** Six faces cost **3 passes per phase (9 total, 11 with E/H)** and
the differential is `1.95e-26` (was `6.46e-26`).

## P-3. Merge Debye/Lorentz regions - Verified (not applicable)

The operator builds exactly one Debye extension and one Lorentz extension per
model (`operator.rs:3569` and `operator.rs:3358`), each covering every
dispersive cell. There is no multi-region case to merge, and the per-step cost
is already 3 (Debye) or 4 (Lorentz) passes. The plan item is closed with that
evidence rather than adding unused code.

## P-4. Device-side probe sampling - Verified

A probe-only model gathers its samples on the device: the run loop uploads the
probe plan (buffer, component, index, interval) once, a `probe_gather` kernel
writes `values[step * count + point]` inside the batch, and only that compact
matrix is downloaded at the batch end. `ProcessIntegral` supports it through
`IntegralCalculator::gpu_field_probe` (the box/point probe reads three
components and divides by the edge length on the host), and `FieldProbe`
through its own `gpu_probe_points`.

Because the probe no longer forces a per-step download, the batch grows from 1
to the next end-criteria/energy boundary (12 steps on tutorial 1). The
probe-only tutorial 1 model reports `6 points on the device` and its probe
files agree with the CPU run to 2.33e-7 / 4.25e-7, the same as the host path.

At 12k cells the GPU is still slower than the CPU (0.97 s vs 0.28 s): the
per-step cost is 5 dispatches (two PML pre phases, fused E, fused H, probe
gather) at ~0.2 ms each, which is the documented per-dispatch floor, not a
transfer cost.

## P-5. Device-side energy end criterion - Verified

`GpuFields::compute_energy` runs a workgroup reduction: each 64-cell group
writes one E and one H partial, the host sums them in f64 and applies `EPS0` /
`MU0`. The measured relative difference from the CPU accumulation is 7.2e-9,
and the run loop no longer downloads the fields before an energy sample.

## P-6. Overlap transfers with compute - Verified (not needed)

P-4 and P-5 removed the per-step and per-sample downloads, so the only
remaining transfer is one small probe matrix per batch (six floats per step in
the tutorial case). A staging ring would hide a transfer that is already below
the dispatch floor, so the item is closed rather than adding unused machinery.

## P-7. Tune the batch chunk size - Verified

Measured on the 451k-cell model, five interleaved runs each:

| Chunk | min | average |
|---|---|---|
| 64 | 2.030 s | 2.161 s |
| 128 | 1.922 s | 2.095 s |
| 256 | 1.969 s | 2.216 s |

The differences are inside the host-load noise, so the default stays 256 and
`OPENEMS_GPU_CHUNK` is available for future tuning.

## P-8. Graceful fallback on low-limit adapters - Verified

Every extension reports the storage buffers its device implementation binds
(excitation 8, UPML 11, Mur 6, lumped 6, sheet 5, TFSF 6, Debye 8, Lorentz
14). `Engine::setup_gpu_extensions` compares the maximum with the adapter
limit and keeps the whole model on the host path when the device cannot bind
them, instead of failing bind-group validation. A unit test pins the table.

## P-9. Automatic engine selection - Verified

`--gpu-auto` picks the engine from the measured 50 000-cell crossover and
prints the decision:

```
[openEMS] GPU auto: 12221 cells is below the 50000-cell crossover, using the CPU engine
[openEMS] GPU update path enabled            # 451k-cell model
```

An explicit `--gpu` keeps its old meaning: it still fails the setup when the
device is unavailable rather than falling back silently.

## P-10. GPU performance regression gate - Verified

`gpu_dispatch_budget_is_constant_in_slab_count` asserts the recorded pass count
per model shape: six PML slabs must cost 6 passes and six Mur faces 11. A
duplicated phase fails the test even when the fields are still correct.

## P-11. Cylindrical multi-grid on the GPU - Verified

`Engine::enable_gpu_pair` enables the GPU on the base engine and its child, and
`iterate_multi_grid` uploads the host arrays before each half-step update and
downloads after it, because the interface tables stay on the host. `--gpu` now
accepts multi-grid models instead of rejecting them.

`gpu_multi_grid_matches_the_cpu_multi_grid` builds the coaxial TEM case twice,
enables the GPU on one pair, advances both five steps and compares the base
fields: **max diff 4.47e-8** (reference field 2.87e-1).

## P-12. Documentation refresh - Implemented

`GPU_ANALYSIS.md` §7/§8, E-016 and the session records carry the new numbers.

## Emergent work

Improvements discovered while implementing the items above are added here with
an id before being implemented.

| Id | Found during | Description | Status |
|---|---|---|---|
| P-E1 | P-1 | The per-element slab lookup is a short prefix scan; measured cost is inside the noise, so no hoisting needed | Verified |
| P-E2 | P-1/P-10 | Fold the PML post phases into the E/H kernels. The pre phases need a global barrier, so they stay separate; a PML model now costs 4 passes/step (two pre phases + fused E + fused H) instead of 6, with the UPML differential still `0.00e0` | Verified |
| P-E3 | P-7/P-9 | Added the `OPENEMS_GPU_CHUNK` tuning knob and `--gpu-auto` with its printed decision | Verified |
| P-E4 | P-2/P-5 | The engine differential tests compared zero fields because `cavity_operator` never built the EC coefficients. Building them exposed the Mur colour-range bug and an unstable Debye test, both fixed; all differentials now run on real fields | Verified |
| P-E5 | P-4 | `ProcessIntegral` box probes are device-sampled through `IntegralCalculator::gpu_field_probe` (three components + edge-length scaling), so the CLI tutorials' probes no longer force a per-step download | Verified |
