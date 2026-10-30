# GPU performance

**NOT MEASURED — no GPU backend exists.**

There is no kernel, no device allocation and no transfer path, so no speedup,
memory or scaling claim can be made. The CPU baseline in
`../performance/CPU_BASELINE.md` is the only performance evidence.

Any future GPU work must record: selected device, driver, kernel build, f32/f64
mode, per-step parity checkpoints, end-to-end wall time including transfers,
and the CPU reference on the same case. Kernel-only timing is not an end-to-end
speedup.
