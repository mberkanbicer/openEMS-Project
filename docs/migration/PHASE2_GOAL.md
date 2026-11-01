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
| E-001 | f32 implemented; long double/MPFR/long integer open | f64 53/53, f32 3/3 |
| E-007 | plan + base/child pair built and unit-tested; coefficient parity open | pair `6x5`/`7x11`; native differential fails (vi 2.03, iv 4.58) |
| GPU | stages 1-3 (device, kernels, Engine) for extension-free models | 48³/120 steps: CPU 5.00 s vs GPU 97 ms, fields identical |
| E-010 | blocked | Actions disabled at account level |

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

## Order of work

1. Fix the cylindrical dual-mesh `vi`/`iv` parity and the closed-alpha seam/
   padding rule; make the base/child operator differential pass.
2. Port the interface interpolation and the multi-grid engine; run the native
   multigrid case.
3. E-001: scalar refactor for non-`Copy` MPFR, then long double and long integer.
4. GPU: extension-aware kernels or a documented host-sync path with a measured
   speed check.
5. E-010 when the environment allows.
