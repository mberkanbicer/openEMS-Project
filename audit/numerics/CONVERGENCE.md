# Convergence and uncertainty

## Status: cavity mesh and time-step refinement recorded; slab and MSL still open

No h / h/2 / h/4 sweep or dt sweep was recorded before this audit.
`VALIDATION.md` labels several cases as "capped/analytic, not converged
scientific acceptance cases". This study closes the cavity and dielectric parts
of that gap.

## Measured: PEC cavity TE101

Harness: `scripts/ci/run_convergence_check_wsl.sh`
(`scripts/ci/convergence_study.py`), Rust Python bindings, deterministic
`EndCriteria=0`, PEC on all six faces, Gaussian 1-10 GHz excitation.
Geometry `a=5 cm, b=2 cm, d=6 cm`; the analytic mode is
`f = c/2 * sqrt((1/a)^2 + (1/d)^2) = 3.9024232466 GHz`.

| Mesh | Cells | Steps | TE101 (Hz) | Relative error | Observed order |
|---|---:|---:|---:|---:|---:|
| 10 x 5 x 12 | 600 | 8 000 | 3.895518e9 | 1.770e-3 | — |
| 20 x 10 x 24 | 4 800 | 16 000 | 3.900757e9 | 4.270e-4 | **2.05** |
| 40 x 20 x 48 | 38 400 | 32 000 | 3.902015e9 | 1.047e-4 | **2.03** |

- All levels are resampled to the **same 72.53 ns window and 65 536 points**
  before the FFT, so the order reflects the mesh, not the frequency-bin width.
- Window: Hann, 32x zero-padding, quadratic peak interpolation.
- Record: `docs/migration/reference-data/convergence/cavity.json`.
- Result: **second-order convergence**, 2.03-2.05, with a monotone error.
  This is the expected Yee order for a smooth cavity mode.

## Measured: dielectric wave speed (plane-wave line)

`cargo run --release -p openems-core --example dielectric_convergence` builds a
120 x 10 x 10 mm parallel-plate line filled with `eps_r = 4` (PEC at z, PMC at
y, PML at the x ends scaled to the mesh), drives a sheet source and correlates
the pulse at 30 and 90 mm.

| Scale | Mesh | dt | Measured (m/s) | Error |
|---:|---|---:|---:|---:|
| 1 | 121 x 11 x 11 | 3.852 ps | 1.495751e8 | 2.143e-3 |
| 2 | 241 x 21 x 21 | 1.926 ps | 1.497239e8 | 1.149e-3 |
| 4 | 481 x 41 x 41 | 0.963 ps | 1.497575e8 | 9.253e-4 |

Analytic `c/2 = 1.498962e8 m/s`. The error decreases monotonically, but the
observed order is **0.90** (h→h/2) and **0.31** (h/2→h/4): below two and falling
at the fine end. The correlation-delay estimator's resolution (~0.1-0.2 %) is
the likely limit, so this study claims **monotone accuracy, not second order**.
Record: `docs/migration/reference-data/convergence/dielectric.json`.

## MSL notch filter (converged)

Harness: `scripts/ci/run_msl_convergence_wsl.sh`
(`scripts/ci/msl_convergence.py`). It re-ran the pinned smoke model with 30 000
steps at three resolutions (divisors 40/50/60). **Correction:** the first run of this
study searched for a minimum of |S11| and therefore reported "no interior
notch". A shunt open stub reflects at its quarter-wave resonance, so the notch
is a **peak** in |S11| (and a dip in |S21|). The corrected observable gives:

| Divisor | Resolution (um) | Notch (GHz) | \|S11\| | \|S21\| | Diff vs finest |
|---:|---:|---:|---:|---:|---:|
| 40 | 559.7 | 3.6703 | 0.9916 | 2.33e-3 | 0.259 MHz (7.1e-5) |
| 50 | 447.7 | 3.6712 | 0.9920 | 3.01e-3 | 1.110 MHz (3.0e-4) |
| 60 | 373.1 | 3.6700 | 0.9921 | 3.14e-3 | reference |

The mesh spread is **3.0e-4** (1.1 MHz) and the finest pair differs by the
same 0.03 %, so the notch is converged at this mesh. The Hammerstad effective
permittivity is 2.8694, giving a quarter-wave estimate of 3.6871 GHz; the
finest notch is 0.46 % below it, as expected from the open-end extension that
the simple formula neglects. Record:
`docs/migration/reference-data/convergence/msl_notch.json`.

## Time-step refinement at fixed mesh (self-convergence)

Same 20x10x24 mesh, `TimeStepFactor` 1.0 / 0.5 / 0.25, step count doubled to
hold a 400 ns window. The reported `solver_dt` confirms the factor is applied
(4.747 / 2.373 / 1.187 ps). A phase-slope estimator (band-passed analytic
signal, 400 ns window, 2.5 MHz raw bin) reproduces the interpolated FFT peak to
six digits, so the frequencies below are genuine, not estimator noise.

| Factor | solver dt (ps) | TE101 (Hz) | Difference vs dt->0 |
|---:|---:|---:|---:|
| 1.00 | 4.747 | 3.900758e9 | +2.062e6 Hz |
| 0.50 | 2.373 | 3.899108e9 | +4.12e5 Hz |
| 0.25 | 1.187 | 3.898696e9 | reference |

At fixed mesh the dt -> 0 limit is the finest step, **3.898696 GHz**, not the
analytic value: the remaining offset is spatial error, which dt refinement
cannot remove. Measured against that limit the temporal error falls from
2.06 MHz to 0.41 MHz, a ratio of 5.0, i.e. **order 2.32** for this one
refinement pair — consistent with second-order time integration within the
resolution of two levels. The 3.73 MHz (9.55e-4) residual against the analytic
mode is the spatial error of the 20x10x24 mesh and must be reduced by h.

The study also exposed and fixed two `TimeStepFactor` defects (RM-172): a factor
>1 was accepted even though native ignores it (it can exceed the CFL limit), and
the XML writer dropped every valid factor <=1 on round-trip. Record:
`docs/migration/reference-data/convergence/cavity_dt.json`.

## Still open

| Case | Status |
|---|---|
| Dielectric slab speed refinement | recorded; monotone but estimator-limited (above) |
| Dielectric slab Fresnel R/T refinement | not run |
| MSL notch S11/S21 refinement | attempted; model has no interior notch (inconclusive, above) |
| Time-step (dt) refinement at fixed mesh | recorded; order 2.32 against the dt->0 limit (above) |
| SAR mesh refinement | not run |
| Non-converging cases | none recorded yet |

Until those are recorded, do not claim general convergence or "second-order
accurate" for every observable; the cavity TE101 result is the one measured
trend.
