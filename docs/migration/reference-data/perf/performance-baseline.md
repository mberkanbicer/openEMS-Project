# Performance and memory baseline vs native (RM-121 / RM-122)

Measured comparison of the Rust solver (`openems-cli`) against the pinned native openEMS on identical input XML. Every number in this file was produced by `scripts/ci/run_performance_baseline_wsl.sh`; nothing is estimated.

- Generated: 2026-10-30 20:04:32 (UTC)
- Repository revision at run time: `c54f55d` (informational; the measured binaries are pinned by their SHA-256 below)
- Native solver: `/home/mberkanbicer/opt/openEMS/bin/openEMS` (openEMS 64bit -- version v0.37.0)
  - SHA-256 `339f2c2e7dbc04f5eb6f8516413e35c4a85bc9f09d81e1b8f91c9845c782bf11`
- Rust solver: `/mnt/c/Users/mberkanbicer/Projects/openEMS-Project-rust/target/release/openems-cli` (built 2026-10-30T19:56:56Z)
  - SHA-256 `2369d8de991fb6bd59d8eaa8c1e8f82a0e7794f532c2864ed1ce37e20d2e3fa5`
- Both binaries are copied into the scratch working directory before the first run, so a rebuild during the measurement cannot mix two executables.
- CPU: Intel(R) Core(TM) i9-14900HX — 32 hardware threads
- Memory: 48025 MiB total
- Kernel: `Linux-6.18.54.1-microsoft-standard-WSL2-x86_64-with-glibc2.43`
- Load average at start: `0.54 0.15 0.05 1/542 528`

## Method

Both solvers run the same materialised `input.xml` per case (SHA-256 below), in their own working directory, one process at a time, with `--exact-endcriteria` so the stopping point is machine independent.

Each solver gets 1 discarded warm-up run(s) followed by 3 measured run(s). Wall time is the best of the measured runs and peak RSS the maximum of the measured runs, both read from `/usr/bin/time -v` (`Elapsed (wall clock) time` and `Maximum resident set size`).

Command form (identical for both solvers, options after the file):

```
/usr/bin/time -v <solver> <case>.xml --exact-endcriteria [<engine option>]
```

The two engine configurations:

- **default** — no engine option, automatic thread count on both sides.
- **basic** — `--engine basic` on both sides: one scalar worker, no SIMD.

The raw `/usr/bin/time -v` output and solver logs of every run are stored next to this file under `raw/`; the solver data files itself (probes, ports, energy dumps) stay in the scratch working directory because they are large and reproducible.

## Inputs

| case | source | XML SHA-256 | cells | dt (ps) |
| --- | --- | --- | --- | --- |
| cavity | `openEMS/TESTSUITE/combinedtests/cavity.m` | `accf81c500d81706…` | 9152 | 3.8089 |
| Coax | `openEMS/TESTSUITE/combinedtests/Coax.m` | `f0629f08a2e6e990…` | 2091200 | 9.6292 |
| msl_port | `openEMS/TESTSUITE/combinedtests/msl_port.m` | `005890289377f70e…` | 14098 | 0.7567 |

## Results — default engine, automatic threads

| case | solver | engine | threads | wall s (best) | wall s (runs) | peak RSS MiB | MCells/s | stop step | wall ratio | RSS ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cavity | native | compressed SSE + multi-threading | 32 | 0.76 | 0.78, 0.79, 0.76 | 46.6 | 240.84 | 20000 | - | - |
| cavity | rust | fastest (threaded kernel) | 32 | 1.86 | 1.86, 1.90, 1.89 | 14.8 | 98.41 | 20000 | 2.45× | 0.32× |
| Coax | native | compressed SSE + multi-threading | 32 | 9.86 | 9.86, 10.67, 10.33 | 249.5 | 249.84 | 1178 | - | - |
| Coax | rust | fastest (threaded kernel) | 32 | 21.95 | 21.95, 23.08, 23.46 | 740.7 | 112.23 | 1178 | 2.23× | 2.97× |
| msl_port | native | compressed SSE + multi-threading | 32 | 0.20 | 0.20, 0.22, 0.22 | 46.7 | 120.96 | 1716 | - | - |
| msl_port | rust | fastest (threaded kernel) | 32 | 0.58 | 0.60, 0.58, 0.64 | 17.6 | 41.71 | 1716 | 2.90× | 0.38× |

## Results — `--engine basic`, one thread

| case | solver | engine | threads | wall s (best) | wall s (runs) | peak RSS MiB | MCells/s | stop step | wall ratio | RSS ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cavity | native | basic | 1 | 1.20 | 1.25, 1.33, 1.20 | 46.0 | 152.53 | 20000 | - | - |
| cavity | rust | basic (serial kernel) | 1 | 1.93 | 2.10, 2.18, 1.93 | 14.8 | 94.84 | 20000 | 1.61× | 0.32× |
| Coax | native | basic | 1 | 25.62 | 25.62, 26.31, 25.73 | 239.8 | 96.15 | 1178 | - | - |
| Coax | rust | basic (serial kernel) | 1 | 42.89 | 45.18, 42.89, 43.30 | 738.4 | 57.44 | 1178 | 1.67× | 3.08× |
| msl_port | native | basic | 1 | 0.31 | 0.31, 0.32, 0.31 | 46.3 | 78.04 | 1716 | - | - |
| msl_port | rust | basic (serial kernel) | 1 | 0.51 | 0.51, 0.53, 0.52 | 17.7 | 47.44 | 1716 | 1.65× | 0.38× |

## Notes

- Peak RSS is the child process peak of `/usr/bin/time -v`, so it excludes the shell and the timing wrapper. It is not directly comparable to RSS of a parallel run with a different thread count; compare only rows with the same engine.
- MCells/s = stop step × cells / wall time, i.e. the measured effective throughput. A run that stops early therefore reports the throughput of the steps it actually executed.
- The native solver prints its engine, grid and timestep; the Rust CLI does not, so the Rust engine label comes from `openEMS/rust-cli/src/main.rs` (engine name → thread count mapping) and is corroborated by the measured CPU utilisation in the CSV.

## Solver agreement

Both solvers simulated the same input, so the stop timestep and the produced output files must agree. Data-row counts and the peak sample magnitude of every output file of the fastest run of each solver (probes, ports, energy dumps):

| config | case | stop step native | stop step rust | output files | agreement |
| --- | --- | --- | --- | --- | --- |
| default | cavity | 20000 | 20000 | 5 | identical row counts |
| default | Coax | 1178 | 1178 | 4 | identical row counts |
| default | msl_port | 1716 | 1716 | 12 | identical row counts |
| basic | cavity | 20000 | 20000 | 5 | identical row counts |
| basic | Coax | 1178 | 1178 | 4 | identical row counts |
| basic | msl_port | 1716 | 1716 | 12 | identical row counts |

Solver differences found while producing this table are recorded in `observed-differences.md` next to this file.
