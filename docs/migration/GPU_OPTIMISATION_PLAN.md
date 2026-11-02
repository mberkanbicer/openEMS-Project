# GPU optimisation plan (2026-11-02)

**Goal:** remove the remaining GPU performance and coverage gaps recorded in
`GPU_ANALYSIS.md` §8 and E-016, in a fixed order, each step gated by a
CPU/GPU differential test and a measured before/after number.

Status values: `Not Started`, `Implemented`, `Verified`, `Blocked`.
Only `Verified` counts as done (AGENTS.md §17).

## Status summary

| Id | Item | Status | Evidence |
|---|---|---|---|
| P-1 | Merge UPML slabs per phase | **Verified** | 6 slabs: 32 -> 6 passes/step; 2-slab differential `0.00e0` |
| P-2 | Colour Mur faces into conflict-free passes | **Verified** | 6 faces: 18 -> 9 passes (11 with E/H); differential `1.95e-26` |
| P-3 | Merge Debye/Lorentz regions | **Verified** | Not applicable by construction: the operator builds exactly one region (`operator.rs:3358/3569`), so the count is already 3/4 |
| P-4 | Device-side probe sampling | Not Started | Analysis: per-step probe output costs ~0.15-0.25 s of a 1.0 s tutorial run; the dispatch count dominates |
| P-5 | Device-side energy criterion | Blocked | f32 GPU reduction would perturb the `endCriteria` stop step; needs a compensated reduction plus stop-step validation |
| P-6 | Overlap transfers with compute | Not Started | — |
| P-7 | Tune the batch chunk size | **Verified** | 64/128/256 within noise (avg 2.16/2.10/2.22 s at 451k); keep 256, `OPENEMS_GPU_CHUNK` knob added |
| P-8 | Graceful fallback on low-limit adapters | **Verified** | Per-extension storage requirement table + engine check |
| P-9 | Automatic engine selection | **Verified** | `--gpu-auto`: CPU at 12 221 cells, GPU at 451k cells |
| P-10 | GPU performance regression gate | **Verified** | Dispatch-budget test (6 slabs -> 6, 6 faces -> 11) |
| P-11 | Cylindrical multi-grid on the GPU | Not Started | — |
| P-12 | Documentation refresh | Implemented | This file, `GPU_ANALYSIS.md` §7/§8, E-016 |

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

## P-4. Device-side probe sampling - Not Started

A probe whose interval rounds to 0 forces a full field download every step.
Measured impact: tutorial 1 costs 1.02 s with no output and 1.16-1.26 s with
per-step probes, so the download is ~0.15-0.25 s of the run; the remaining
~0.8 s is the 12 passes/step, which P-1/P-2 and the planned PML fusion reduce.
Doing this item without the fusion would optimise the smaller term.

## P-5. Device-side energy end criterion - Blocked

`calc_fast_energy` accumulates in `f64`; the GPU has no `f64`. A plain `f32`
partial-sum reduction changes the energy ratio by ~1e-7, which can move the
`endCriteria` stop step. The item needs a compensated (Kahan) reduction and a
test that the tutorials stop at the identical timestep; until then the CPU
value is kept so the stop step cannot drift.

## P-6. Overlap transfers with compute - Not Started

The batch still ends with `map_async` + `poll(wait)`. A staging ring that
starts the next batch before mapping the previous slot would hide the wait; it
is only worth it once P-4/P-5 make the download the dominant term again.

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

## P-11. Cylindrical multi-grid on the GPU - Not Started

`--gpu` still rejects multi-grid models. This is the largest remaining item:
the split/interpolation phases need device kernels and their own differential
harness.

## P-12. Documentation refresh - Implemented

`GPU_ANALYSIS.md` §7/§8, E-016 and the session records carry the new numbers.

## Emergent work

Improvements discovered while implementing the items above are added here with
an id before being implemented.

| Id | Found during | Description | Status |
|---|---|---|---|
| P-E1 | P-1 | The per-element slab lookup is a short prefix scan; measured cost is inside the noise, so no hoisting needed | Verified |
| P-E2 | P-1/P-10 | PML still costs 4 of the 6 passes of a PML-only model (24 of 32 for six slabs). Folding the PML terms into the E/H kernels (as native does) is the next big win for small/medium PML models | Not Started |
| P-E3 | P-7/P-9 | Added the `OPENEMS_GPU_CHUNK` tuning knob and `--gpu-auto` with its printed decision | Verified |
