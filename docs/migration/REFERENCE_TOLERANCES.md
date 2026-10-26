# Reference differential tolerances (RM-119, proposed)

Status: **proposed** by the migration work, pending owner approval. Every bound
is a *differential* bound between two implementations of the same
discretisation; it is not a physics acceptance limit and it is never widened to
hide a difference.

Harness: `scripts/ci/reference_harness.py` (wrapper
`scripts/ci/run_reference_harness_wsl.sh`). Each case runs the unmodified pinned
source against the Rust core, keeps the solver output (`input.xml`, port and
probe files, HDF5 dumps) and compares the derived quantities with the native
capture under `docs/migration/reference-data/`.

## Bounds

| Quantity | Bound | Justification |
| --- | --- | --- |
| `Z_ref` (real part, `f > 0.1 f_stop`) | 1 % relative | The staircase discretisation dominates; the two native runs differ by < 1e-3 relative, so 1 % leaves room for the floating-point path difference without hiding a regression |
| `S21` | 0.05 dB absolute | Transmission is smooth and lossless; the native run spread is 0.012 dB |
| `S11` (worst return loss in band) | 2 dB absolute | S11 is a deep null (down to -50 dB); a relative bound is meaningless there, so the worst value is compared in dB |
| Conducting-sheet `|T|` | 0.2 dB absolute | The source test allows 0.25 dB; the differential bound is tighter because the discretisation is shared |
| Conducting-sheet phase | 2 deg absolute | The source test allows 10 deg for the same reason |
| Solver text outputs (port/probe rows) | 1 % relative RMS of the peak | Same mesh and timestep; only the arithmetic order differs |
| HDF5 field snapshots | 1 % relative RMS of the peak | As above, per dataset |

## Measured differences (2026-10-26)

| Case | Check | Measured | Verdict |
| --- | --- | --- | --- |
| coax (3-D, 715 k cells) | `Z_ref` real | 7.5e-5 relative | PASS |
| coax | `S21` | 1.9e-4 dB | PASS |
| coax | `S11` worst | -50.83 dB vs -50.88 dB (0.05 dB) | PASS |
| conducting sheet (resistive film) | `|T|` | 3.07 dB | **FAIL** (RM-139) |
| conducting sheet | phase | 6.0-12.9 deg | **FAIL** (RM-139) |
| fieldprobes | D = eps0 E | passes after the EPS0 fix | PASS |
| fieldprobes | FD dump vs FD probe | ~1.0 relative | **FAIL** (RM-140) |
| msl-notchfilter | `et` / `ht` | 2.1e-6 relative | PASS (after the fix) |
| msl-notchfilter | `port_ut_*`, `port_it_2*` | 1.4e-8 .. 6.0e-6 | PASS |
| msl-notchfilter | `port_it_1A/1B` (excited port) | Rust output is all zeros (native peak 9.6e-8 / 8.4e-8) | **FAIL** (RM-141) |

The conducting-sheet and fieldprobes failures are real findings, not tolerance
problems: the harness compares the same physical case, and the gaps are
explained by open defects (`REMEDIATION_TASKS.md` RM-139, RM-140).

## Rule

A bound may only change together with a recorded measurement that justifies it
and an owner-approved decision in `VALIDATION.md`. A failing case is never
resolved by widening its bound.
