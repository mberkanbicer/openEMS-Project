# Gold results (recorded)

Categories: **A** analytic, **D** pinned native parity, **E** backend-to-backend
(no GPU backend, so E is empty). Artifact hashes: `GOLD_REGISTRY.json`.

## A — analytic

| Case | Observable | Result | Bound |
|---|---|---|---|
| Vacuum pulse | propagation speed | error < 2 % | 2 % (Yee dispersion) |
| Dielectric slab | speed `c/sqrt(eps_r)` | error < 2 % | 2 % |
| Uniform-field SAR | `sigma|E|²/(2 rho)` | `local_sar_matches_the_definition` (unit case) | exact |

## Convergence (category A, measured)

| Case | h | h/2 | h/4 | Observed order |
|---|---|---|---|---|
| PEC cavity TE101 | 1.770e-3 | 4.270e-4 | 1.047e-4 | 2.05, 2.03 |

Dielectric speed (eps_r=4) at h/h2/h4: 2.14e-3, 1.15e-3, 9.25e-4; monotone,
observed order 0.90/0.31 (estimator-limited; no second-order claim).

MSL shunt-open-stub notch at 373/448/560 um: 3.6700 / 3.6712 / 3.6703 GHz,
spread 3.0e-4; quarter-wave estimate 3.6871 GHz (0.46 % high, open-end
extension not modelled). The earlier "no interior notch" record was wrong:
it searched for a |S11| minimum, but a shunt open stub reflects at resonance
(`|S11|` peak, `|S21|` 2-3e-3).

Time-step refinement at 4.75/2.37/1.19 ps: against the fixed-mesh dt->0 limit
(3.898696 GHz) the temporal error falls 2.06 MHz -> 0.41 MHz, ratio 5.0
(order 2.32 for one refinement pair). The 3.73 MHz offset from the analytic
mode is spatial error. Record: `reference-data/convergence/cavity_dt.json`.

Common 72.53 ns window, 65 536 points, Hann, 32x zero-padding. Record:
`docs/migration/reference-data/convergence/cavity.json`. Slab/MSL/dt refinement
is still open.

## D — native parity (recorded)

| Gate | Result |
|---|---|
| Operator dump (`vv/vi/ii/iv`) | vv exact, vi 1.3e-13, ii 6e-8, iv 4.8e-15 |
| UPML reflection | probes 6.0e-8 / 1.0e-8 |
| 51-case differential harness | all cases within `REFERENCE_TOLERANCES.md` |
| Coax 3-D | Z_ref 7.5e-5, S21 1.9e-4 dB, S11 0.05 dB |
| Conducting sheet | 0.036-0.073 dB, 0.178-0.199° |
| MSL notch | 2.1e-6 relative (et/ht), ports 1.4e-8..6.0e-6 |
| Cylindrical SAR | per-cell 2.6e-3 (bound 1e-2), peak 1e-3 |
| Curve excitation | peak 4.753e-5, max sample 1.617e-4 |
| NF2FF | every dataset 1.6e-5 of peak |
| Native field dump (`.vts`) | bit-identical (200 points, 0.0) |
| Octave testsuite | 10/10 |
| Python native suites | 405 pass, 2 GPU skipped |

## E — backend comparison

None: no SIMD variant, no GPU backend, no alternate engine.

## C — CST

None: no data (`cst/RESULTS.md`).

## Caveat

The D results prove the port matches the pinned native implementation on the
same discretisation. They do **not** prove discretisation accuracy; that needs
the convergence study in `CONVERGENCE.md`. Reference artifacts are never
regenerated from the code under test.
