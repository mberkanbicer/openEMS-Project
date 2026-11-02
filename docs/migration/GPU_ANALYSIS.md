# GPU analysis and optimisation (2026-11-02)

**Scope:** complete read of the GPU path, a per-step cost model, measured
before/after numbers, and the remaining bottleneck with a concrete plan.
Related records: ADR 0012 (GPU update kernels), E-016 (host-sync
characteristic), RM-188/RM-189.

## 1. What the GPU path does today

The engine has two GPU paths (`openEMS/rust/src/engine.rs`):

| Path | Trigger | What runs where |
|---|---|---|
| **Batched kernels** | `--gpu`, model with **no** engine extension | E/H kernels on the device; one command submission per batch; one host download per batch |
| **Host-extension** | `--gpu`, any extension (UPML/PML, excitation, Mur, TFSF, lumped, Debye/Lorentz, sheets) | E/H kernels on the device; every extension phase on the CPU with upload/download around it |

`GpuFields` (`openEMS/rust/src/gpu.rs`) owns the device buffers:

- persistent `volt`/`curr` (3·nx·ny·nz f32 each);
- the four EC coefficient arrays (`vv`, `vi`, `ii`, `iv`) uploaded once at setup;
- one WGSL module with `update_e`/`update_h`;
- persistent map-read staging buffers (one per field plus one pair buffer) and
  a reused upload scratch, added in this session so a sync no longer allocates
  multi-megabyte buffers.

`FDTD_FLOAT` is `f32`, and the WGSL kernels perform the same arithmetic in the
same order as the CPU kernels. That is why the differential tests show a
bit-identical field after a run (`E diff 0.00e0`).

## 2. Per-step cost model (before this session)

The run loop called `iterate_ts(1)` once per timestep, and every call ended
with `sync_gpu_fields()` — a full download of both fields. A host-extension
step paid, per step:

| Item | Count (before) | Count (now) |
|---|---|---|
| Command submissions (E dispatch, H dispatch) | 2 | 2 |
| Download submissions + queue waits | 2 submissions, 2 waits | 2 submissions, 2 waits |
| Array transfers (volt/curr, each direction) | 8 (4 up, 4 down) | 6 (4 up, 2 down) |
| Field downloads for an extension-free step | 1 full download **per step** | 1 full download **per batch** |
| Command submissions for a batch of N extension-free steps | 2N | 1 per 256 steps |

The extension-free path was therefore transfer-bound: measured cost per step
scaled with the cell count (11k cells → 0.22 ms/step, 451k cells → 5.15 ms/step)
while the kernels themselves are ~0.01–0.2 ms/step on the same grids.

## 3. Changes made

1. **Batched submissions** (`GpuFields::dispatch_steps`): N complete E/H steps
   are recorded into one command buffer (chunked at 256 steps) and submitted
   once. The fields stay resident between steps.
2. **Run-loop batching** (`OpenEMS::run_fdtd`): a GPU run advances by
   `min(next probe/dump interval, next Nyquist end-criteria sample, excitation
   max-energy sample, remaining steps)` instead of one step, so a batch ends
   exactly where a consumer becomes due. The processing array gained
   `steps_until_due`/`is_due` for this.
3. **One round trip per batch** (`GpuFields::download_pair` + `gpu_pending`):
   the batch end copies both fields into one staging buffer, maps once and
   clears the pending flag; the extra `sync_fields` calls in the loop are
   no-ops when nothing changed.
4. **Per-field dirty tracking on the host path** (`host_volt_dirty` /
   `host_curr_dirty`): the E phase uploads only what changed, and each phase
   downloads only the field it produced (volt after E, curr after H), halving
   the download traffic and removing the redundant full re-upload before H.
5. **Persistent staging/upload buffers**: no per-sync allocation.
6. **Device-side excitation** (RM-190): the source is uploaded once and applied
   by an `apply_source` kernel inside the batch, with per-step uniforms bound by
   dynamic offset; the extension's host phases become no-ops when every
   extension is device-native (`is_gpu_native`), so source-only models take the
   batched path.

Nothing in the numerical path changed: the CPU engine is untouched, and the
tutorial CPU output is byte-identical to the recorded hashes
(`probe_near` SHA-256 `620f048d…50bd`), while the device source is bit-identical
to the host source (`0.00e0`).

## 4. Measurements (Windows, RTX 5070 Laptop, 2026-11-02)

### Engine unit scenarios (48³ = 110k cells, 120 steps)

| Scenario | CPU | GPU before | GPU now | Speed-up vs CPU |
|---|---|---|---|---|
| extension-free kernels | 224 ms | 31 ms | **13.3 ms** | **16.9x** |
| host-extension path | 218 ms | 2470 ms | **384 ms** | 0.57x (6.4x better than before) |

### CLI, extension-free models

| Model | Steps | CPU | GPU before | GPU now | Speed-up |
|---|---|---|---|---|---|
| 41×21×13 (11k cells) bare cavity | 12 000 | 1.72–1.89 s | 2.67 s | **1.11–1.15 s** | **1.55x** (was 0.6x) |
| 121×61×61 (451k cells) bare cavity | 2 000 | 11.7–11.8 s | 10.31 s | **1.63–1.74 s** | **7.2x** (was 1.1x) |

The CPU timing of the large case varies with host load (11.7 s to 21.2 s in
the interleaved samples); the GPU time is stable at ~1.7 s.

### CLI, models with extensions (the real-world case)

| Model | Extension | CPU | GPU before | GPU now |
|---|---|---|---|---|
| tutorial 1 (PML on two faces) | UPML | 0.370 s | 1.277 s | 1.277 s |
| tutorial 3 (PEC cavity + excitation primitive) | excitation | 3.754 s | 13.19 s | 16.97 s |

These are the models the host-extension path exists for, and they are still
slower on the GPU. See §5.

### Correctness

The GPU and CPU runs of tutorials 1 and 3 agree to

| Probe | max abs difference | relative |
|---|---|---|
| `probe_near` (700 steps) | 2.5e-7 V/m | 2.8e-7 |
| `probe_far` (700 steps) | 4.1e-7 V/m | 4.7e-7 |
| `probe_left` (12 000 steps) | 4.7e-7 V/m | 1.6e-5 of the 0.03 V/m peak |
| `probe_right` (12 000 steps) | 4.8e-7 V/m | 1.6e-5 |

The engine-level differential (`gpu_engine_matches_cpu_on_a_cavity`,
`gpu_host_extension_path_matches_the_cpu_engine`) asserts `< 1e-5` and reports
`0.00e0` at 120 steps.

## 5. Device-side excitation (RM-190)

The first extension ported to the device is the excitation source, because
every real model has one. `EngineExtExcitation` already owns per-edge
component/position/amplitude lists and the waveform samples, so the GPU path
uploads them once:

- one storage buffer per side (flat N-I-J-K index, amplitude, delay, period,
  signal slot, signal length);
- one concatenated waveform buffer (one slot per distinct `Arc<Excitation>`);
- a uniform with the per-step `ts`, bound with a dynamic offset so a whole
  batch records one dispatch per step without rewriting it.

`apply_source` reproduces `EngineExtExcitation::sample_index` exactly, and the
engine marks the extension `gpu_handled` so its host phases become no-ops. When
**every** registered extension is device-native, the model takes the batched
path; a mixed model (e.g. UPML + source) keeps the host path, because the host
array is authoritative between host extension phases.

### Measurements

| Scenario | CPU | GPU (host path, before) | GPU (device source) |
|---|---|---|---|
| engine 24³, 120 steps, source | — | — | field diff **0.00e0**, batch vs single-step **0.00e0** |
| large cavity 121×61×61, 2000 steps, source, no output | 20.1–20.5 s | not measured (host path) | **2.15–2.19 s (9.2x)** |
| tutorial 3 (11k cells, 12 000 steps, per-step probes + dump) | 3.10 s | 16.97 s | **9.93 s** |
| tutorial 3, `OverSampling=1` (probe every 13 steps) | 1.90 s | — | **2.22 s** |
| tutorial 3, source only (no probes/dump) | 1.72 s | — | **1.96 s** |

Tutorial 3 probe agreement against the CPU run: max 5.15e-7 V/m
(`probe_left`), 5.11e-7 V/m (`probe_right`).

### Why the small source model is only at parity

At 11k cells the kernels cost ~0.1 s for 12 000 steps while each host sync
costs ~1 ms, and the run loop syncs once per end-criteria sample (every
`nyquist` steps) and once per probe/dump step. The tutorial sets
`OverSampling=16` with a 13-step Nyquist, so its probes sample **every step**
and each step pays a full field download — that is output cost, not physics,
and the native engine pays it too. At 451k cells the same structure gives 9.2x.

The remaining extension work is UPML (see §6): a PML model keeps the host path
until the four PML phases have device kernels.

## 6. Device-side UPML (RM-191)

The second extension ported to the device is UPML, which covers every model
with PML boundaries. `EngineExtUPML` stores, per slab, six coefficient arrays
(`vv`, `vvfo`, `vvfn`, `ii`, `iifo`, `iifn`) and two flux arrays; the host
phases are four closed-form updates. The GPU path:

- concatenates the three components of each slab array and uploads the eight
  arrays once (the flux arrays are the kernel state);
- binds them with the two global field buffers and a uniform holding the global
  dims, the slab origin and the slab extent;
- dispatches four kernels (`upml_pre_volt`, `upml_post_volt`,
  `upml_pre_curr`, `upml_post_curr`) at the same points as the host phases,
  so a batch records `pre_volt* -> E -> post_volt* -> source -> pre_curr* -> H
  -> post_curr* -> source` per step;
- raises the requested `max_storage_buffers_per_shader_stage` to 16 (the
  device default of 8 cannot hold the two fields, six coefficients and two
  flux arrays; every desktop adapter offers more).

The differential test `gpu_device_upml_matches_the_cpu_engine` (12³, 120 steps,
two slabs, non-trivial coefficients) reports `CPU diff 0.00e0` and batch vs
single-step `0.00e0`; tutorial 1 probes agree with the CPU run to 2.33e-7 /
4.25e-7 V/m.

### Measurements

| Scenario | CPU | GPU |
|---|---|---|
| 201×51×51 (525k cells), PML on both x faces + source, 700 steps | 12.2–14.0 s | **2.55–2.60 s (4.8–5.5x)** |
| tutorial 1 (12k cells), per-step probes + dump | 0.38–0.61 s | 1.67–1.75 s |
| tutorial 1, `OverSampling=1` (probe every 12 steps) | 0.35–0.38 s | 1.16–1.26 s |
| tutorial 1, no probes/dump | 0.31–0.33 s | 1.02–1.04 s |

### Why the small PML model is slower

At 12k cells the four UPML kernels plus E/H/source are 11 dispatches per step,
and each dispatch costs ~0.1 ms of driver overhead on this adapter while the
work itself is microseconds. The CPU solves the same step in ~0.45 ms. This is
the per-dispatch overhead floor, not a defect in the port: the same structure
wins 4.8–5.5x at 525k cells and 9.2x on the large source model. Folding the
PML terms into the E/H kernels (native fuses them) would remove four dispatches
per step and is the next optimisation if small-model GPU use matters.

## 7. Device-side Mur ABC and the remaining extensions

### Mur (`EngineExtMurABC`, RM-192)

Mur owns per-face coefficient and history arrays and three voltage-phase
updates (`pre`, `post`, `apply2`). The device port uploads every face's
`coeff_p`/`coeff_pp` and history arrays once and binds them with the global
voltage buffer and a uniform holding the global dims, the face line/shift and
the axis mapping (`dir`, `dir+1`, `dir+2`). Because Mur faces overlap on
corner edges and the host applies them in registration order, the kernels run
one pass per face in that order (pre, then post, then apply2), interleaved as
`mur_pre -> upml_pre -> E -> upml_post -> mur_post -> mur_apply -> source ->
upml_pre_curr -> H -> upml_post_curr -> source`.

Validation: `gpu_device_mur_matches_the_cpu_engine` (12³, 120 steps, two
overlapping faces) reports `CPU diff 6.46e-26` and batch vs single-step
`0.00e0`; a 201×51×51 Mur model with a source (700 steps) runs in
**2.30–2.77 s** on the GPU against 10.2–11.4 s on the CPU (**3.9–4.4x**), and
its probe signals agree with the CPU run to 3.78e-7 / 2.91e-7 V/m.

### Lumped RLC (`EngineExtLumpedRLC`, RM-193)

Lumped elements are independent edges with three-sample voltage/current history
and a parallel inductor current. The device port packs the nine coefficients per
edge into one buffer and keeps the history on the device; `lumped_pre` rotates
the voltage history and advances the inductor current, `lumped_apply` performs
the series update and writes the edge voltage back. They run in the
`pre_voltage` and `apply2_voltage` slots, i.e. `mur_pre -> lumped_pre ->
upml_pre -> E -> upml_post -> mur_post -> lumped_apply -> mur_apply -> source`.

Validation: `gpu_device_lumped_rlc_matches_the_cpu_engine` (12³, 120 steps,
three edges) reports `CPU diff 0.00e0` and batch vs single-step `0.00e0`.

### Conducting sheet (`EngineExtConductingSheet`, RM-194)

The sheet is a two-order ADE over a set of cells. The device port packs the
per-order/component internal and external coefficients and the ADE state into
global (order, component, position) matrices, plus one component-0 base index
per cell; `sheet_pre` advances the ADE state and `sheet_apply` subtracts the
sum of the two orders from the three components. They run in the
`pre_voltage` and `apply2_voltage` slots, after the lumped phases.

Validation: `gpu_device_conducting_sheet_matches_the_cpu_engine` (12³, 120
steps, two cells, non-trivial coefficients) reports `CPU diff 3.94e-31` and
batch vs single-step `0.00e0`.

### TFSF (`EngineExtTFSF`, RM-195)

A plane-wave TFSF region corrects two edges per surface cell on each face, with
a per-term amplitude, delay and interpolation factor, reading the excitation
waveform at `ts - delay` (folded by the signal period, floored at 0). The
device port uploads, per direction and side, the flattened
(index, amplitude, delay, delta) tables and the waveform samples once; the
per-step timestamp arrives in a dynamic uniform slot and `tfsf_apply`
reproduces `update_delay_lookup` + `add_sample` exactly.

Faces of one direction sit on opposite planes and never share an edge, but
**corners are shared between directions**, and the host applies them in
`n`-outer order. A single dispatch over all terms raced on those corner edges
(the first differential run showed a 6.7e-4 field error), so the kernels run
one pass per direction in that order.

Validation: `gpu_device_tfsf_matches_the_cpu_engine` (16³, 120 steps, six
active faces, synthetic delay/amplitude tables) reports `CPU diff 1.16e-10`
and batch vs single-step `0.00e0`; a 101×61×61 model with a TFSF plane wave
and six PML faces (400 steps) runs in **2.46–3.16 s** on the GPU against
10.8–10.9 s on the CPU (**3.4–4.4x**), and its probe signal agrees with the
CPU run to 2.11e-9 V/m.

### Debye and Lorentz (`EngineExtDebyeMaterial`, `EngineExtLorentzMaterial`, RM-196/RM-197)

Debye keeps a per-pole state over the dispersive cells and runs three voltage
phases (pole update, implicit solve, correction). The device port packs the
pole coefficients and state as (pole, component, position) and runs
`debye_pre`, `debye_post` and `debye_apply` in the pre/post/apply2 slots.

Lorentz has four phases (voltage and current ADE) and runs them as
`lorentz_pre_volt`, `lorentz_pre_curr`, `lorentz_apply_volt` and
`lorentz_apply_curr`, with the per-order active flags uploaded once and the
sequential per-order subtraction preserved so the rounding matches the host.

Validation: `gpu_device_debye_matches_the_cpu_engine` reports `CPU diff
1.14e-13` and `gpu_device_lorentz_matches_the_cpu_engine` `5.46e-12`; both are
`0.00e0` for batch vs single-step.

### Coverage

Every engine extension now has a device implementation: excitation, UPML, Mur,
lumped RLC, conducting sheet, TFSF, Debye and Lorentz. A model is batched when
all of its extensions are device-native; the host-sync path remains only as the
fallback for any future extension without a device port.

## 8. Practical guidance (current state)

- `--gpu` wins on models from roughly 50k cells upward: 7.2x extension-free at
  451k cells, 9.2x source-driven at 451k cells, 4.8–5.5x with PML at 525k
  cells. Below that the per-dispatch and per-sync overhead dominates.
- Per-step output (probes whose `OverSampling` makes the interval round to
  zero, dumps written every step) forces one host download per step on any
  engine, CPU or GPU. Runs with sparse output see the kernel speed-up.
- The GPU never changes the result: the differential gates compare the fields
  (`0.00e0` on the kernel, device-source and device-UPML tests) and the
  tutorials agree to ~5e-7 V/m.

## 9. Reproduce

```powershell
# engine differentials
cargo test --release -p openems-core --features "hdf5 gpu" engine::tests::gpu -- --nocapture

# CLI scenarios (bare models: no probes/dumps/extensions)
target\release\openems-cli.exe 04_large_bare.xml --gpu

# tutorial, outputs compared against the CPU run
target\release\openems-cli.exe tutorials\03_rectangular_cavity.xml --gpu
```
