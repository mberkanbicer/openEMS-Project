# CPU performance baseline (refreshed at the audit tree)

Source: `docs/migration/reference-data/perf/performance-baseline.md` and
`.csv`, measured 2026-10-30 with
`scripts/ci/run_performance_baseline_wsl.sh --runs 3`.
Measured revision `c54f55d`; binaries pinned by SHA-256 in the report.

## Environment

| Item | Value |
|---|---|
| CPU | Intel Core i9-14900HX, 32 hardware threads |
| RAM | 48 GB |
| OS | Windows 11 + WSL2 Ubuntu, kernel 6.18.54.1 |
| Native | openEMS v0.37.0 (`~/opt/openEMS/bin/openEMS`), SHA-256 `339f2c2e…` |
| Rust | `openems-cli` release, SHA-256 `2369d8de…` |
| Build | Cargo release, `opt-level = 3` |

## Default engine (automatic threads, 32)

| Case | Cells | Native wall | Rust wall | Wall ratio | Rust MCells/s | Native MCells/s | RSS ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| cavity | 9 152 | 0.76 s | 1.86 s | **2.45x** | 98.4 | 240.8 | 0.32x |
| Coax | 2 091 200 | 9.86 s | 21.95 s | **2.23x** | 112.2 | 249.8 | 2.97x |
| msl_port | 14 098 | 0.20 s | 0.58 s | **2.90x** | 41.7 | 121.0 | 0.38x |

## `--engine basic` (one scalar worker, no SIMD)

| Case | Native wall | Rust wall | Wall ratio | RSS ratio |
|---|---:|---:|---:|---:|
| cavity | 1.20 s | 1.93 s | **1.61x** | 0.32x |
| Coax | 25.62 s | 42.89 s | **1.67x** | 3.08x |
| msl_port | 0.31 s | 0.51 s | **1.65x** | 0.38x |

## Interpretation

- The Rust solver is **1.6-2.9x slower** than the native SSE/multithreaded
  engine on these cases; it is not faster.
- The scalar parity is close (1.6x); the remaining gap is the compressed-SSE
  kernel and its cache behavior.
- Memory: small cases use 0.32-0.38x native RSS; the 2.09 M-cell Coax case uses
  2.97-3.08x because the Rust operator keeps full `f32` field and coefficient
  arrays.
- Both solvers reach the same stop step (`--exact-endcriteria`), so the
  comparison is work-equivalent.

## Proposed gate (owner approval pending)

For each recorded configuration/case, median/best of 5 interleaved runs on the
same host: wall ≤4.0x native, peak RSS ≤3.25x native, no case regressing >20 %
against its recorded value. `scripts/ci/check_performance_baseline.py` evaluates
this on the CSV.

Recorded run: **PASS** for all six rows (max wall 2.90x, max RSS 3.08x).
The gate is not yet an accepted acceptance criterion.
