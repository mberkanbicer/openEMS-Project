# CPU comparison — knobs, threads and what was measured

All data from `docs/migration/reference-data/perf/performance-baseline.md`
(2026-10-27). Not re-run here.

## Threaded ("fastest") vs serial ("basic")

| Case | Native threaded | Rust threaded | Ratio | Native serial | Rust serial | Ratio |
|---|---:|---:|---:|---:|---:|---:|
| cavity | 1.34 s | 5.07 s | 3.78x | 2.81 s | 5.10 s | 1.81x |
| Coax | 24.99 s | 53.53 s | 2.14x | 42.38 s | 111.29 s | 2.63x |
| msl_port | 0.51 s | 1.49 s | 2.92x | 0.69 s | 1.40 s | 2.03x |

Threading helps the Rust engine (5.07 vs 5.10 for cavity is noise; Coax 53.5
vs 111.3 is ~2x). The native SSE engine gains more on the small cavity.

## Throughput

Rust threaded: cavity 36.1, Coax 46.0, msl_port 16.2 MCells/s. Native threaded:
136.6 / 98.6 / 47.4. The gap is the compressed-SSE kernel and its cache
behavior, not a correctness issue.

## What was not measured

- No SIMD-specific variant was benchmarked separately; the Rust engine is
  scalar/threaded.
- No NUMA, cache-miss or instruction-count profiling is recorded.
- No GPU comparison exists (no GPU backend).
- Warm-up/thermal effects are only partially controlled (two runs per config).

## Optimization status

No optimization was attempted in this audit. The prompt's Phase 5 requires a
verified baseline and per-change measurement; that baseline exists, but the
acceptance threshold is not agreed (`PERF-001`). Optimization work should not
start before the P0 correctness guards and the convergence study are in place.
