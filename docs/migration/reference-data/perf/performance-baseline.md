# Performance and memory baseline vs native (RM-121 / RM-122)

Measured comparison of the Rust solver (`openems-cli`) against the pinned native openEMS on identical input XML. Every number in this file was produced by `scripts/ci/run_performance_baseline_wsl.sh`; nothing is estimated.

- Generated: 2026-10-27 23:13:02 (UTC)
- Repository revision at run time: `f1cdbe5` (informational; the measured binaries are pinned by their SHA-256 below)
- Native solver: `/home/mberkanbicer/opt/openEMS/bin/openEMS` (openEMS 64bit -- version v0.37.0)
  - SHA-256 `339f2c2e7dbc04f5eb6f8516413e35c4a85bc9f09d81e1b8f91c9845c782bf11`
- Rust solver: `/mnt/d/openEMS-Project-rust/target/release/openems-cli` (built 2026-10-27T22:05:39Z)
  - SHA-256 `7e0522fcab7aa1c288fe77cfe1e99e3476e558922bc81f3f6739e1638e8b8266`
- Both binaries are copied into the scratch working directory before the first run, so a rebuild during the measurement cannot mix two executables.
- CPU: 13th Gen Intel(R) Core(TM) i9-13900H — 20 hardware threads
- Memory: 48026 MiB total
- Kernel: `Linux-6.18.54.1-microsoft-standard-WSL2-x86_64-with-glibc2.43`
- Load average at start: `0.99 0.29 0.10 1/331 491`

## Method

Both solvers run the same materialised `input.xml` per case (SHA-256 below), in their own working directory, one process at a time, with `--exact-endcriteria` so the stopping point is machine independent.

Each solver gets 1 discarded warm-up run(s) followed by 2 measured run(s). Wall time is the best of the measured runs and peak RSS the maximum of the measured runs, both read from `/usr/bin/time -v` (`Elapsed (wall clock) time` and `Maximum resident set size`).

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
| cavity | native | compressed SSE + multi-threading | 20 | 1.34 | 1.49, 1.34 | 46.5 | 136.60 | 20000 | - | - |
| cavity | rust | fastest (threaded kernel) | 20 | 5.07 | 5.07, 5.21 | 14.7 | 36.10 | 20000 | 3.78× | 0.32× |
| Coax | native | compressed SSE + multi-threading | 20 | 24.99 | 25.48, 24.99 | 249.4 | 98.58 | 1178 | - | - |
| Coax | rust | fastest (threaded kernel) | 20 | 53.53 | 53.53, 53.73 | 738.6 | 46.02 | 1178 | 2.14× | 2.96× |
| msl_port | native | compressed SSE + multi-threading | 20 | 0.51 | 0.53, 0.51 | 46.8 | 47.44 | 1716 | - | - |
| msl_port | rust | fastest (threaded kernel) | 20 | 1.49 | 1.49, 1.52 | 17.8 | 16.24 | 1716 | 2.92× | 0.38× |

## Results — `--engine basic`, one thread

| case | solver | engine | threads | wall s (best) | wall s (runs) | peak RSS MiB | MCells/s | stop step | wall ratio | RSS ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cavity | native | basic | 1 | 2.81 | 2.86, 2.81 | 45.9 | 65.14 | 20000 | - | - |
| cavity | rust | basic (serial kernel) | 1 | 5.10 | 5.30, 5.10 | 14.7 | 35.89 | 20000 | 1.81× | 0.32× |
| Coax | native | basic | 1 | 42.38 | 51.56, 42.38 | 239.5 | 58.13 | 1178 | - | - |
| Coax | rust | basic (serial kernel) | 1 | 111.29 | 111.29, 118.63 | 738.3 | 22.14 | 1178 | 2.63× | 3.08× |
| msl_port | native | basic | 1 | 0.69 | 0.69, 0.70 | 46.3 | 35.06 | 1716 | - | - |
| msl_port | rust | basic (serial kernel) | 1 | 1.40 | 1.40, 1.41 | 18.0 | 17.28 | 1716 | 2.03× | 0.39× |

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
