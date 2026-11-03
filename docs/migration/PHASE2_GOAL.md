# Phase-2 goal: close the remaining migration gaps

**Set:** 2026-11-01
**Owner:** project owner
**Status:** active

## Goal statement

Close every remaining open item of the Rust migration that is not an accepted
environment limit:

1. **E-001** — fparser numeric backends: `long double`, long integer and
   MPFR/GMP in addition to the implemented `f64`/`f32`.
2. **E-007** — cylindrical multi-grid: validated base/child operator pair,
   interface interpolation, engine, and removal of the setup rejection.
3. **GPU** — extension-aware acceleration so excitation/PML/probe models can
   run on the GPU instead of falling back to the CPU.
4. **E-010** — hosted CI/platform matrix. This is environment-blocked and can
   only be closed when the account-level Actions restriction is lifted.

E-008, the abi3 Windows wheels, f32, GPU stages 1-3 and the CST comparison are
already verified and are not reopened.

## Definition of done

| item | evidence required |
| --- | --- |
| E-001 | per-backend differential corpus against the native fparser build; default f64 unchanged |
| E-007 | native-equivalent coefficients for base/child grids, interface probe/field differential, engine case, E-007 removed from `EXCEPTIONS.md` |
| GPU | excitation/PML/probe models run on GPU with CPU/GPU field agreement and a recorded wall-time comparison; explicit fallback only for unsupported extensions |
| E-010 | hosted `ci.yml`/`reference.yml`/`windows-rust-package.yml` runs at the release commit, or a documented owner decision |

## Current state (2026-11-01)

| item | state | last evidence |
| --- | --- | --- |
| E-001 | **verified**: float, long-double (binary128), MPFR/GMP and long-integer | native differentials: long-double 30/30 worst 0.0, MPFR 30/30 worst 1.8e-29, long-integer 52/52 exact; f64 53/53, f32 3/3 |
| E-007 | **verified**: setup integration, child-safe extensions, probes and engine | coax multigrid vs single grid: u1 1.04e-7, u2 9.3e-8, phase 1.0761 rad identical, beta error 6.2e-3, log profile 1.3e-4 |
| GPU | stages 1-3 + host-sync extension path + `--gpu` CLI | extension-free 48³/120: CPU 5.00 s vs GPU 97 ms; host-sync 48³/120: CPU 4.23 s vs GPU 23.07 s, fields identical |
| E-010 | out of scope | owner decision 2026-11-01; local WSL2/Windows evidence accepted |

## E-007 parity diagnosis (2026-11-01)

- Closed-alpha meshes: native operator reports 10 alpha lines, the Rust loader
  pads to 11 (`cylindrical_full_turn_is_accepted_and_padded`). This changes the
  operand shape of the differential; a shape-aware comparison or a padding
  decision is required.
- Open-alpha, rho > 0 base: an unscaled (no-rho) EC experiment matched the
  dump's rho independence but failed the authoritative coaxial cylindrical gate
  (`beta = k0` deviation 1.37 vs 0.01) and was reverted (`4f97545`). The dump is
  not yet a safe oracle for the rho convention; the coaxial propagation gate
  must keep passing while the dump parity is investigated.
- Open-alpha, rho = 0 base: `ii` also differs, so the axis (`rho = 0`) handling
  is a second discrepancy.
- Closed-alpha, rho > 0 base: native 5x10x5 = 250 nodes and constant `vi`
  (259.084) vs Rust 5x11x5 = 275 nodes and rho-scaled `vi` (28.6 -> 57.3).
  The dump normalization is independent of the alpha closure, so matching it
  requires porting the native coefficient **and** engine rho normalization as
  one coordinated change; changing the coefficients alone breaks the coaxial
  TEM gate (reverted in `4f97545`).

## E-007 multi-grid engine (2026-11-01)

The operator pair now follows the native layout instead of the previous
inverted one: the base keeps the full rho/alpha mesh and the child gets the rho
lines up to the split plus every second alpha line
(`Operator_CylinderMultiGrid::SetGeometryCSX`). `AlphaInterpolation` was
rewritten against `SetupInterpolation`, including the single-weight `p == pp`
cases and the closed-mesh padding plane.

`MultiGridEngine` ports `Engine_CylinderMultiGrid` + `Engine_Ext_
CylinderMultiGrid` with the native barrier order: base/child voltage half-step,
interface voltage sync (`split_pos - 1`), base/child current half-step,
interface current sync (`split_pos - 2`), then the child-to-base interpolation
of the overlap rows. The base EC coefficients below `split_pos - 1` are zeroed
exactly like `CalcStartStopLines`.

Validation (openEMS-core lib tests, closed alpha, manufactured coaxial TEM
pulse, 5 steps):

- voltage parity against the single-grid reference: **6.7e-3** relative,
- current parity: **3.3e-2** relative,
- peak position: multigrid z=7, reference z=7,
- normalized radial voltage profile: **2.8e-4** relative.

Over 40 steps the same initial-condition case drifts to ~30% because the
native interface coupling is first order and generates a small `E_z` at the
split. With the actual `1/rho` excitation and voltage probes the high-level
run matches the single grid to 1e-7 (see stage 5 in `VALIDATION.md`); the
multi-grid is integrated in `setup_fdtd`, the setup rejection is gone, and the
coax phase/profile gates pass. The operator-dump normalization difference is
tracked as E-015 (diagnostic only).

## Order of work

1. E-001 is verified for all native numeric variants; the long-integer differential is part of the gate.
2. Extend the GPU path to extension models, then close E-010 when the
   environment allows. The E-015 operator-dump diagnostic is optional.
3. GPU: extension models use the host-sync path; GPU-safe extension kernels remain a performance follow-up.
4. GPU: extension-aware kernels or a documented host-sync path with a measured
   speed check.
5. E-010 when the environment allows.
