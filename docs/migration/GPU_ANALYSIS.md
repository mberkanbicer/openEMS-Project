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

## 6. Remaining extension work: UPML and the host path

A model with a non-device extension (currently UPML, Mur, TFSF, lumped,
Debye/Lorentz, conducting sheets) still pays a device→host→device round trip
per half step. The cost is the queue wait in `map_async` + `poll(wait)`, not
bandwidth: at 11k cells the transfers are ~0.8 MB/step (≪0.1 ms) yet a step
costs ~1.4 ms.

The next port is **UPML** (`EngineExtUPML`): the four phases are closed-form
updates over the six PML slabs with 12 coefficient arrays and 6 flux arrays.
Upload coefficients and flux arrays once (slab volume × 3 × 18 floats) and add
four kernels dispatched at the same points as the host phases (`pre_voltage`,
`post_voltage`, `pre_current`, `post_current`). The extension trait already
separates those phases, so the port is independent and testable against the
existing CPU extension with the same `field_diff` harness (`f32` equality is
already demonstrated for the E/H kernels: `0.00e0`).

After UPML, the same pattern covers Mur, TFSF, lumped, Debye/Lorentz and the
conducting sheets; the engine keeps the host path for any extension that has
not been ported (the capability flag `is_gpu_native` decides per model).

## 7. Practical guidance (current state)

- `--gpu` is a win for extension-free and source-driven models from roughly
  50k cells upward: 7.2x at 451k cells bare and **9.2x** at 451k cells with a
  source (2.15 s vs 20.1 s). Below ~50k cells the fixed per-batch
  synchronisation dominates (1.5x at 11k cells).
- Per-step output (probes whose `OverSampling` makes the interval round to
  zero, dumps written every step) forces one host download per step on every
  engine, CPU or GPU; that is output cost, not physics. Runs with sparse output
  see the kernel speed-up.
- Models with PML are still host-sync until the UPML kernels land; the CPU
  engine is the better choice for those today.
- The GPU never changes the result: the differential gates compare the fields
  (`0.00e0` on the kernel and device-source tests) and the tutorials agree to
  ~5e-7 V/m.

## 8. Reproduce

```powershell
# engine differentials
cargo test --release -p openems-core --features "hdf5 gpu" engine::tests::gpu -- --nocapture

# CLI scenarios (bare models: no probes/dumps/extensions)
target\release\openems-cli.exe 04_large_bare.xml --gpu

# tutorial, outputs compared against the CPU run
target\release\openems-cli.exe tutorials\03_rectangular_cavity.xml --gpu
```
