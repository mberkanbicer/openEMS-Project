# CPU comparison — knobs and throughput

Data: refreshed baseline at `c54f55d` (`performance-baseline.md`, 3 measured
runs after a warm-up). Not a new optimization.

## Threading effect (default vs basic)

| Case | Rust basic | Rust default | Speed-up | Native basic | Native default | Speed-up |
|---|---:|---:|---:|---:|---:|---:|
| cavity | 1.93 s | 1.86 s | 1.04x | 1.20 s | 0.76 s | 1.58x |
| Coax | 42.89 s | 21.95 s | 1.95x | 25.62 s | 9.86 s | 2.60x |
| msl_port | 0.51 s | 0.58 s | 0.88x (overhead) | 0.31 s | 0.20 s | 1.55x |

The threaded Rust engine scales on the large Coax case but the small cavity and
msl_port gain little or lose to thread overhead. Native's SSE kernel scales
better on all three.

## Throughput (default)

Rust: 98.4 / 112.2 / 41.7 MCells/s (cavity / Coax / msl).
Native: 240.8 / 249.8 / 121.0 MCells/s.

The gap is the compressed-SSE implementation and memory traffic, not a
correctness issue; the same stop step and fields are used.

## What was not measured

- No separate SIMD variant (the Rust engine is scalar + threads).
- No NUMA/cache-miss/instruction profiling.
- No GPU comparison (no GPU backend).
- Only 3 measured runs; host is shared with the WSL acceptance work.

## Optimization status

No optimization was attempted in this audit. The baseline and the proposed gate
are in place; optimization should follow the P0/correctness and convergence
work, with paired before/after runs.
