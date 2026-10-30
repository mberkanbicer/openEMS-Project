# CPU performance baseline

Source: `docs/migration/reference-data/perf/performance-baseline.md`
(measured 2026-10-27, binaries pinned by SHA-256). **Not re-run in this audit**;
the numbers below are recorded evidence, not a new measurement.

## Environment

| Item | Value |
|---|---|
| CPU | 13th Gen Intel Core i9-13900H, 20 hardware threads |
| RAM | 48 GB |
| OS | Windows 11 + WSL2 Ubuntu, kernel 6.18.54.1 |
| Native | openEMS v0.37.0 (`~/opt/openEMS/bin/openEMS`), SHA-256 `339f2c2e…` |
| Rust | `openems-cli` release, SHA-256 `7e0522fc…` |
| Build | Cargo release, `opt-level = 3`; native SSE + multithreading |

## Cases (same XML, same final step)

| Case | Cells | dt (ps) | Native wall (s) | Rust wall (s) | Ratio | Rust MCells/s |
|---|---:|---:|---:|---:|---:|---:|
| cavity | 9 152 | 3.8089 | 1.34 | 5.07 | 3.78x | 36.1 |
| Coax | 2 091 200 | 9.6292 | 24.99 | 53.53 | 2.14x | 46.0 |
| msl_port | 14 098 | 0.7567 | 0.51 | 1.49 | 2.92x | 16.2 |

Serial kernel comparison (no threading): 1.81x / 2.63x / 2.03x native.

## Interpretation

- The Rust solver is **2-4x slower** than the native SSE/multithreaded engine on
  these three cases; it is not claimed to be faster.
- The Rust engine is memory-efficient on small cases (RSS 0.32x) and heavier on
  the 2.1 M-cell Coax case (2.96x) — see `MEMORY_AND_IO.md`.
- No performance requirement was ever agreed, so this is a baseline, not a
  pass/fail (`FINAL_AUDIT.md` criterion 10).

## Proposed gate (needs owner approval)

For each recorded case, median of 5 interleaved runs on the same host:
no case above 4x native wall; no case regressing >20 % against its recorded
median; peak RSS ≤3.25x native or an absolute cap; report MCells/s, peak RSS,
final step and binaries' SHA-256. Cold start measured separately.
