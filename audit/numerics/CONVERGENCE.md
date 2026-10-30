# Convergence and uncertainty

## Status: NOT RUN — no refinement study exists

No h / h/2 / h/4 mesh sweep or dt sweep is recorded. `VALIDATION.md` explicitly
labels several cases as "capped/analytic, not converged scientific acceptance
cases". The only analytic observables are vacuum and dielectric propagation
speed (2 % discrete bound).

## Why this matters

The differential harness compares the Rust solver with the pinned native
implementation on the **same mesh and time step**. That proves porting fidelity
(category D), not discretisation accuracy against physics. Without a refinement
series, the observed order and the asymptotic error of S-parameters, resonance
frequency and SAR are unknown.

## Planned study (smallest useful set)

| Case | Observables | Meshes | Acceptance |
|---|---|---|---|
| PEC cavity | first 2-3 resonances | h, h/2, h/4 | monotone error, observed order ≈ 2 for smooth modes; report the actual order |
| Dielectric slab | Fresnel R/T at normal incidence | h, h/2, h/4 | error decreases; energy budget closes within 1 % |
| MSL notch | S11/S21, notch frequency | native graded mesh, +25 %, +50 % lines | notch frequency stable within the differential bound; report drift |
| Uniform-field SAR | local SAR | h, h/2 | analytic `2.5e-4 W/kg` at `sigma=0.5, rho=1000, E_peak=1` |

Each case records `dt`, cells, wall time, the observable, the analytic or
converged reference, the observed order and the cost. Non-converging cases are
published, not hidden.

## Uncertainty budget

- Native parity: bounds in `REFERENCE_TOLERANCES.md` (Z_ref 1 %, S21 0.05 dB,
  S11 2 dB, sheet 0.2 dB/2°, fields 1 % RMS).
- Analytic wave speed: 2 % (dominated by Yee dispersion at the test resolution).
- No CST or measurement uncertainty exists (no data).

Until the study is recorded, any statement of the form "converged" or
"second-order accurate" is unsupported for this port.
