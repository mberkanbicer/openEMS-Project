# Convergence and uncertainty

## Status: cavity mesh refinement recorded; slab, MSL and time-step refinement still open

No h / h/2 / h/4 sweep or dt sweep was recorded before this audit.
`VALIDATION.md` labels several cases as "capped/analytic, not converged
scientific acceptance cases". This study closes the first part of that gap.

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

## Time-step refinement (inconclusive at this record length)

Same 20x10x24 mesh, `TimeStepFactor` 1.0 / 0.5 / 0.25, step count doubled to
keep the physical window. The reported `solver_dt` confirms the factor is
applied (4.747 / 2.373 / 1.187 ps).

| Factor | solver dt (ps) | TE101 (Hz) | Relative error |
|---:|---:|---:|---:|
| 1.00 | 4.747 | 3.900757e9 | 4.270e-4 |
| 0.50 | 2.373 | 3.899107e9 | 8.498e-4 |
| 0.25 | 1.187 | 3.898695e9 | 9.554e-4 |

The total variation (2.1 MHz) is **below the 13.3 MHz raw FFT bin** of the
72.5 ns record, so this run does **not** establish a temporal order and does not
show temporal error; a longer record or a phase-based estimator is required.
Record: `docs/migration/reference-data/convergence/cavity_dt.json`.

The run also exposed and fixed two `TimeStepFactor` defects (RM-172): a factor
>1 was accepted even though native ignores it (it can exceed the CFL limit), and
the XML writer dropped every valid factor <=1 on round-trip.

## Still open

| Case | Status |
|---|---|
| Dielectric slab Fresnel R/T refinement | not run |
| MSL notch S11/S21 refinement | not run |
| Time-step (dt) refinement at fixed mesh | attempted; inconclusive at the 13.3 MHz bin (above) |
| SAR mesh refinement | not run |
| Non-converging cases | none recorded yet |

Until those are recorded, do not claim general convergence or "second-order
accurate" for every observable; the cavity TE101 result is the one measured
trend.
