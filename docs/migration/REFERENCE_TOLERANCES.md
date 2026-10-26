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
| conducting sheet (resistive film) | `|T|` | 0.036 dB vs native | PASS |
| conducting sheet (thin copper) | `|T|` | 0.036 dB vs native | PASS |
| conducting sheet (thick copper) | `|T|` | 0.073 dB vs native | PASS |
| conducting sheet | phase | 0.178-0.199 deg vs native | PASS |
| fieldprobes | all checks | probes 1.5e-5, Ef/Hf 1.2e-5, H TD 3e-5 | PASS |
| msl-notchfilter | `et` / `ht` | 2.1e-6 relative | PASS (after the fix) |
| msl-notchfilter | `port_ut_*`, `port_it_2*` | 1.4e-8 .. 6.0e-6 | PASS |
| msl-notchfilter | `port_it_1A/1B` (excited port) | Rust probe is a y-only line, native is a y-z surface (all-zero current) | **FAIL** (RM-141) |

The conducting-sheet gap was the incident field, not the sheet model:
Rust cleared only the tangential current components on PMC faces while native
also clears the normal one on the low face and the outermost line of every
axis, which made the 1 mm PEC/PMC channel propagate at 0.69 c. With the native
rules the incident probe matches exactly and all three sheet cases pass. The
remaining MSL failure (`port_it_1A/1B`) is the Python `MSLPort` current-probe
geometry, tracked as RM-141. HDF5 snapshots are normalised by the peak of the
whole file, not per timestep, so late near-zero snapshots are compared against
a meaningful scale.

## Rule

A bound may only change together with a recorded measurement that justifies it
and an owner-approved decision in `VALIDATION.md`. A failing case is never
resolved by widening its bound.
