# Differences observed while measuring the baseline (RM-121 / RM-122)

This file records solver differences that surfaced while producing
`performance-baseline.md`. They are **not** part of the timing/memory
comparison; they are recorded here so the evidence is not lost, and they are
reported automatically by `scripts/ci/performance_baseline.py` ("output is
identically zero in the Rust run").

All numbers below were measured with the exact binaries the table pins:

- native `/home/mberkanbicer/opt/openEMS/bin/openEMS`,
  SHA-256 `339f2c2e7dbc04f5eb6f8516413e35c4a85bc9f09d81e1b8f91c9845c782bf11`
  (openEMS v0.37.0)
- Rust `target/release/openems-cli`,
  SHA-256 `34589b24a80ee9e0e8ef6c7373f2140f754d0aaef8fbe42e589ba30154657e63`
  (built 2026-10-27T14:04:37Z)

## 1. `combinedtests/cavity`: the voltage probes are identically zero in the Rust run

Input: the unmodified testsuite case, XML SHA-256
`accf81c500d8170617be836b4b5fa1b6d610b88c909aea56e364dc8774868a33`
(9152 cells, dt = 3.8089 ps, 20000 timesteps on both sides, all six boundaries
PEC).

Reproduction:

```bash
octave --no-gui --quiet --eval \
  "addpath('scripts/ci'); materialize_perf_cases('/tmp/cavity-check','cavity');"
mkdir -p /tmp/cavity-check/native /tmp/cavity-check/rust
(cd /tmp/cavity-check/native && ~/opt/openEMS/bin/openEMS /tmp/cavity-check/cavity.xml --exact-endcriteria)
(cd /tmp/cavity-check/rust   && <repo>/target/release/openems-cli /tmp/cavity-check/cavity.xml --exact-endcriteria)
```

Peak magnitude of the second column (the first column is the time axis):

| output | native rows | rust rows | native peak | rust peak |
| --- | --- | --- | --- | --- |
| `ut1x` (voltage) | 6667 | 6667 | 5.807240e-06 | **0.000000e+00** |
| `ut1y` (voltage) | 6667 | 6667 | 2.316510e-05 | **0.000000e+00** |
| `ut1z` (voltage) | 6667 | 6667 | 7.766348e-06 | **0.000000e+00** |
| `et` (energy) | 168 | 168 | 9.986930e-01 | 9.986928e-01 |
| `ht` (energy) | 168 | 168 | 9.999650e-01 | 9.999648e-01 |

So the simulation itself is fine — both solvers stop at the same timestep, the
row counts are identical and the global energy histories agree to 2e-7
relative — but every voltage probe is written as an exact zero.

Scope checks that were run (each a 300-step variant of the same XML):

- one-edge probe and two-edge probe: both zero;
- probe moved to the cavity centre (0.01..0.012, 0.012, 0.02): zero;
- `zmax` changed to `PML_8`: zero.

Scope checks that exclude the harness as the cause:

- the XML is written by the testsuite's own `WriteOpenEMS`, not hand-made;
- the same binary produces **correct** voltage probes elsewhere: `Coax` `ut1`
  (8.1952e-04 in both solvers) and all six `msl_port` `port_ut1*` probes match
  native to the printed precision, so this is not "voltage probes are broken";
- re-scaling `msl_port` from millimetres to metres (`DeltaUnit` 1e-3 -> 1, an
  identical physical model) still matches native, so `DeltaUnit = 1` is not the
  trigger.

Why the testsuite did not catch it: `openEMS/TESTSUITE/helperscripts/check_frequency.m`
compares the spectrum against `max(val)`. With an all-zero spectrum `max(val)`
is 0, and both the "inside" test (`max(val) >= max1*rel`) and the "outside" test
(`max(val) <= max1*rel`) hold for zero, so `combinedtests/cavity` can pass
vacuously. A per-case row in `VALIDATION.md` that only records PASS therefore
does not prove the probes carried signal.

Status: **fixed** by RM-149 (2026-10-27). The excitation setup now walks a
`Curve` primitive with the native `Operator::FindPath` and excites every edge on
the path. Re-measured on the same case:

| output | native peak | Rust peak |
| --- | --- | --- |
| `ut1x` | 5.807240e-06 | 5.807516e-06 |
| `ut1y` | 2.316510e-05 | 2.316531e-05 |
| `ut1z` | 7.766348e-06 | 7.766571e-06 |

With the native timestep pinned in the XML (`<FDTD TimeStep="3.808880293356461e-12">`)
all 6667 samples of all three probes are bit-identical, so the remaining
relative difference (4.8e-5 / 9.2e-6 / 2.9e-5 on the peaks, up to 1.6e-4 per
sample) is the pre-existing `calc_timestep` summation-order difference, not the
excitation. The dedicated gate is
`scripts/ci/run_curve_excitation_check_wsl.sh`. The harness keeps its
"identically zero in the Rust run" warning as a regression guard.

Wire primitives are deliberately **not** walked: native `ToCurve()` accepts only
`Type == CURVE`, and a `<Wire>` excitation is excited through the containment
path (which a thin wire does not satisfy), so both solvers report zero for it.
