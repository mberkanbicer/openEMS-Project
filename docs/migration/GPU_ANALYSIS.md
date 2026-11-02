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

Nothing in the numerical path changed: the CPU engine is untouched, and the
tutorial CPU output is byte-identical to the recorded hashes
(`probe_near` SHA-256 `620f048d…50bd`).

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

## 5. Remaining bottleneck: the host-extension path

Every extension phase runs on the CPU, so a PML or excitation model pays a
device→host→device round trip per half step. The cost is dominated by the
queue waits in `map_async` + `poll(wait)`, not by bandwidth: at 11k cells the
transfers are ~0.8 MB/step (≪0.1 ms) yet the step costs ~1.4 ms.

The only structural fix is to run the extensions on the device. Concretely:

1. **GPU-side excitation** (`EngineExtExcitation`): the extension already owns
   the per-edge index/coefficient lists. Upload them once, upload the waveform
   samples once, and add an `apply2` kernel that reads the per-step scalar from
   a uniform (dynamic offsets for a batch). A model whose only extension is the
   excitation then becomes extension-free on the host and uses the batched path
   (tutorial 3 would drop from ~17 s to the kernel-bound ~1–2 s).
2. **GPU-side UPML** (`EngineExtUPML`): the four phases are closed-form updates
   over the six PML slabs with 12 coefficient arrays and 6 flux arrays. Upload
   the coefficients/flux arrays once (they are small: slab volume × 3 × 18) and
   add four kernels, dispatched at the same points as the host phases. That
   removes the round trip from every PML model.
3. **Extension capability flag**: add an optional trait method
   (`fn gpu_supported(&self) -> bool`) so the engine keeps the fast path when
   every extension has a device implementation, and falls back to host-sync
   otherwise (Mur/TFSF/lumped/Debye/Lorentz remain host-side until ported).

The extension trait already separates the six phases, so each port is
independent and testable against the existing CPU extension with the same
`field_diff` harness (f32 CPU/GPU equality is achievable and already
demonstrated for the kernels).

## 6. Practical guidance (current state)

- `--gpu` is a win from roughly 50k cells upward for extension-free models
  (7x at 450k cells measured here); below that the fixed per-batch
  synchronisation dominates (1.5x at 11k cells).
- For models with PML or a source region, the CPU engine is still faster at
  tutorial scale; the gap shrinks as the kernel work grows relative to the
  sync cost (the 48³ engine test is within 2x of the CPU).
- The GPU never changes the result: the differential gates compare the fields
  and the tutorials agree to ~1e-6 V/m.

## 7. Reproduce

```powershell
# engine differentials
cargo test --release -p openems-core --features "hdf5 gpu" engine::tests::gpu -- --nocapture

# CLI scenarios (bare models: no probes/dumps/extensions)
target\release\openems-cli.exe 04_large_bare.xml --gpu

# tutorial, outputs compared against the CPU run
target\release\openems-cli.exe tutorials\03_rectangular_cavity.xml --gpu
```
