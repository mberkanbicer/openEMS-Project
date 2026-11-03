# Error budget

## 1. Differential (Rust vs pinned native, same discretisation)

Source: `docs/migration/REFERENCE_TOLERANCES.md` (status: **proposed**, pending
owner approval) and `VALIDATION.md`.

| Quantity | Bound | Measured example |
|---|---|---|
| `Z_ref` real, `f > 0.1 f_stop` | 1 % relative | 7.5e-5 (Coax) |
| `S21` | 0.05 dB absolute | 1.9e-4 dB |
| `S11` worst in band | 2 dB absolute | -50.83 vs -50.88 dB |
| Conducting sheet `|T|` | 0.2 dB | 0.036-0.073 dB |
| Conducting sheet phase | 2° | 0.178-0.199° |
| Port/probe text rows | 1 % RMS of peak | 1.4e-8 .. 6.0e-6 |
| HDF5 field snapshots | 1 % RMS of peak | probes 1.5e-5, fields 1.2e-5 |
| Cylindrical SAR | per-cell 1e-2 | 2.6e-3; peak 1e-3; counters equal |
| Curve excitation | peak rel. | 4.753e-5 |

These bounds are differential: they catch porting regressions, not physics
error. They must not be widened to hide a difference (project rule D-07).

## 2. Analytic

| Observable | Bound | Basis |
|---|---|---|
| Vacuum wave speed | 2 % | Yee numerical dispersion at the test resolution (20 samples/cell? see test) |
| Dielectric wave speed | 2 % | same |
| Local SAR (planned) | exact formula | `σ|E_peak|²/(2ρ)`; not yet a test |

## 3. Floating point

- Fields are `f32`, setup/accumulators `f64`, same as native.
- Denormal/FTZ behavior is set explicitly (`denormal.rs`) and tested.
- Reduction order/threading can differ from native; the differential harness
  includes threaded runs and the bounds above absorb it. No bitwise claim is
  made for threaded runs.
- No FMA/`-ffast-math` toggle is documented; release uses Cargo `opt-level=3`.

## 4. Unknowns

- No CST/measurement uncertainty (no data).
- No mesh/time discretisation uncertainty (no refinement study).
- The differential tolerances are proposed, not owner-approved.

Any numeric claim in the release note must cite this file and state which class
(A analytic, D native parity, E backend) it belongs to.
