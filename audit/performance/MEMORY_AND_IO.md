# Memory and I/O

Source: same recorded baseline (2026-10-27). Not re-run.

## Peak RSS (threaded / serial)

| Case | Native | Rust | Ratio |
|---|---:|---:|---:|
| cavity | 46.5 MiB | 14.7 MiB | 0.32x |
| Coax | 249.4 MiB | 738.6 MiB (threaded), 738.3 MiB (serial) | 2.96x / 3.08x |
| msl_port | 46.8 MiB | 17.8 MiB | 0.38x |

The Rust operator keeps all six field arrays plus `vv/vi/ii/iv` in `f32`
(`12 * cells * 4` bytes), which dominates the Coax case (2.1 M cells). Native's
compressed-SSE operator stores a more compact coefficient representation, which
explains the 3x peak on the large case.

## I/O

- HDF5 writes are not part of the measured wall time (the baseline stops after
  stepping). No I/O throughput benchmark is recorded.
- The HDF5 feature is optional; a build without it cannot write native field
  dumps (E-002).
- Async dumps are not implemented; the engine writes at the requested cadence
  on the stepping thread. A large dump therefore stalls the run. This is a
  potential P2 improvement, not measured.

## Gaps

- No allocation-rate or peak-memory profile per phase.
- No large-model (>5 M cells) memory test.
- No streaming/chunked dump path.
