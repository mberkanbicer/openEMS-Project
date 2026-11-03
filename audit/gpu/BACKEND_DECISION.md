# GPU backend decision

## Decision: no GPU compute backend in the Rust port (accepted scope)

- The Rust workspace has **no FDTD GPU code**: no CUDA/HIP/Metal/Vulkan compute
  kernels, no device enumeration, no GPU engine selection. `wgpu` is used for
  the 3D viewport only.
- This is a documented scope decision (ADR 0002; `docs/migration/audits/upstream-sync-2026-10-30.md`,
  "GPU engine, HIP/Metal plugins, device listing … no GPU engine in the Rust
  port (ADR 0002); recorded as a scope decision").
- The upstream C++ tree **does** carry GPU backends
  (`openEMS/FDTD/gpu_backend*`, `hip/`, `metal/`, `python/Tests/GPU_Engine.py`);
  the Rust port is therefore behind upstream in this area (`UPSTREAM_DELTA`).

## What this means for users

- `engine='gpu'` in the Python API now raises a clear `RuntimeError` (RM-168)
  instead of silently running the CPU engine.
- The carried `Test_GPUPlugins` tests are reported `SKIPPED: NO GPU BACKEND` in
  the acceptance report; they are never recorded as passed.
- No GUI or CLI flag advertises GPU acceleration.

## If a GPU backend is funded later

Follow the prompt's Phase 6: choose the backend from measured hardware
capability, keep a CPU reference, prove per-extension parity before claiming
speed, and never hide host round-trips. A first backend on this host would be
CUDA/HIP-class; `wgpu` f64 compute is not portable (`SHADER_F64` is
Vulkan/SPIR-V-only on many adapters).
