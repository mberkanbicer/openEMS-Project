# Performance and memory baseline vs native (RM-121 / RM-122)

Measured comparison of the Rust solver (`openems-cli`) against the pinned native openEMS on identical input XML. Every number in this file was produced by `scripts/ci/run_performance_baseline_wsl.sh`; nothing is estimated.

- Generated: 2026-10-27 19:38:29 (UTC)
- Repository revision at run time: `f9d462220c0c` (informational; the measured binaries are pinned by their SHA-256 below)
- Native solver: `/home/mberkanbicer/opt/openEMS/bin/openEMS` (openEMS 64bit -- version v0.37.0)
  - SHA-256 `339f2c2e7dbc04f5eb6f8516413e35c4a85bc9f09d81e1b8f91c9845c782bf11`
- Rust solver: `/mnt/c/Users/mberkanbicer/.copilot/repos/copilot-worktrees/openEMS-Project/mberkanbicer-potential-garbanzo/target/release/openems-cli` (built 2026-10-27T14:04:37Z)
  - SHA-256 `34589b24a80ee9e0e8ef6c7373f2140f754d0aaef8fbe42e589ba30154657e63`
- Both binaries are copied into the scratch working directory before the first run, so a rebuild during the measurement cannot mix two executables.
- CPU: 13th Gen Intel(R) Core(TM) i9-13900H — 20 hardware threads
- Memory: 48026 MiB total
- Kernel: `Linux-6.18.54.1-microsoft-standard-WSL2-x86_64-with-glibc2.43`
- Load average at start: `0.55 0.19 0.07 1/348 520`

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
| cavity | native | compressed SSE + multi-threading | 20 | 0.83 | 0.83, 0.85 | 46.6 | 220.53 | 20000 | - | - |
| cavity | rust | fastest (threaded kernel) | 20 | 10.50 | 14.71, 10.50 | 14.7 | 17.43 | 20000 | 12.65× | 0.32× |
| Coax | native | compressed SSE + multi-threading | 20 | 11.36 | 11.52, 11.36 | 249.5 | 216.85 | 1178 | - | - |
| Coax | rust | fastest (threaded kernel) | 20 | 25.18 | 25.18, 25.19 | 738.6 | 97.83 | 1178 | 2.22× | 2.96× |
| msl_port | native | compressed SSE + multi-threading | 20 | 0.25 | 0.25, 0.25 | 46.9 | 96.77 | 1716 | - | - |
| msl_port | rust | fastest (threaded kernel) | 20 | 1.78 | 2.04, 1.78 | 17.8 | 13.59 | 1716 | 7.12× | 0.38× |

## Results — `--engine basic`, one thread

| case | solver | engine | threads | wall s (best) | wall s (runs) | peak RSS MiB | MCells/s | stop step | wall ratio | RSS ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cavity | native | basic | 1 | 1.43 | 1.43, 1.44 | 46.4 | 128.00 | 20000 | - | - |
| cavity | rust | basic (serial kernel) | 1 | 2.43 | 2.69, 2.43 | 14.6 | 75.33 | 20000 | 1.70× | 0.32× |
| Coax | native | basic | 1 | 29.44 | 29.91, 29.44 | 239.6 | 83.68 | 1178 | - | - |
| Coax | rust | basic (serial kernel) | 1 | 54.28 | 55.08, 54.28 | 738.6 | 45.38 | 1178 | 1.84× | 3.08× |
| msl_port | native | basic | 1 | 0.39 | 0.39, 0.40 | 46.3 | 62.03 | 1716 | - | - |
| msl_port | rust | basic (serial kernel) | 1 | 0.74 | 0.74, 0.80 | 17.6 | 32.69 | 1716 | 1.90× | 0.38× |

## Notes

- Peak RSS is the child process peak of `/usr/bin/time -v`, so it excludes the shell and the timing wrapper. It is not directly comparable to RSS of a parallel run with a different thread count; compare only rows with the same engine.
- MCells/s = stop step × cells / wall time, i.e. the measured effective throughput. A run that stops early therefore reports the throughput of the steps it actually executed.
- The native solver prints its engine, grid and timestep; the Rust CLI does not, so the Rust engine label comes from `openEMS/rust-cli/src/main.rs` (engine name → thread count mapping) and is corroborated by the measured CPU utilisation in the CSV.

## Solver agreement

Both solvers simulated the same input, so the stop timestep and the produced output files must agree. Data-row counts of every output file of the fastest run of each solver (probes, ports, energy dumps):

| config | case | stop step native | stop step rust | output files | agreement |
| --- | --- | --- | --- | --- | --- |
| default | cavity | 20000 | 20000 | 5 | row counts equal, **zero output in Rust** |
| default | Coax | 1178 | 1178 | 4 | identical row counts |
| default | msl_port | 1716 | 1716 | 12 | identical row counts |
| basic | cavity | 20000 | 20000 | 5 | row counts equal, **zero output in Rust** |
| basic | Coax | 1178 | 1178 | 4 | identical row counts |
| basic | msl_port | 1716 | 1716 | 12 | identical row counts |

Solver differences found while producing this table are recorded in
`observed-differences.md` next to this file.
