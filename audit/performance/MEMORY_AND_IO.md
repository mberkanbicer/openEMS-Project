# Memory and I/O

Data: refreshed baseline at `c54f55d` (3 measured runs).

## Peak RSS

| Case | Native | Rust | Ratio | Config |
|---|---:|---:|---:|---|
| cavity | 46.6 MiB | 14.8 MiB | 0.32x | default (32 threads) |
| Coax | 249.5 MiB | 740.7 MiB | 2.97x | default |
| msl_port | 46.7 MiB | 17.6 MiB | 0.38x | default |
| Coax | 239.8 MiB | 738.4 MiB | 3.08x | basic (1 thread) |

The operator keeps six field arrays plus `vv/vi/ii/iv` in `f32`
(`12 * cells * 4` bytes), which dominates the 2.1 M-cell Coax case. Native's
compressed-SSE operator stores a more compact coefficient representation. Small
cases are much lighter than native because there is no VTK/Qt runtime.

## I/O

- HDF5 writes are outside the measured wall time (the baseline stops after
  stepping). No I/O throughput benchmark is recorded.
- The HDF5 feature is optional; without it, native field dumps cannot be written
  (E-002).
- Dumps are written on the stepping thread; a large dump stalls the run. No
  async dump queue is implemented or measured.

## Gaps

- No allocation-rate or per-phase memory profile.
- No >5 M-cell model test.
- No streaming/chunked dump path.
- Peak RSS is the child-process peak from `/usr/bin/time -v`; do not mix thread
  counts when comparing.
