# Conducting-Sheet WSL Reference

This directory contains a compact reference set from the pinned
`openEMS/python/Tests/Conducting_Sheet.py` analytic transmission test.

- Root repository: `974294ba7d812ef5a46a4760593057aee7ce6866`
- `openEMS` submodule: `305df56aa7df4d2f18c687083f484a96f9a22610`
- Input SHA-256: `0d2f987e1391763bb2446b45a424246f9d2058f08fa89fcc1c68fc0d4dcb64f9`
- Environment: Ubuntu 26.04.1 under WSL, GCC/G++ 15.2.0, openEMS 0.37.0,
  Python 3.14.4, NumPy 2.3.5, HDF5 1.14.6; Intel Core i9-13900H, 20 logical
  CPUs
- Grid: 3x3x601 cells (5,409 total), 0.25 mm axial spacing, 1 GHz to 10 GHz
  output band sampled at 91 frequencies

The test simulates an empty 1D channel and the same channel with a resistive
film, thin copper, and thick copper sheet. All four reached the configured
-50 dB end criterion, with `exact_endcriteria=True`, at 1,460 steps for the
empty channel and 1,314 steps for each sheet case. The test's source limits
are: resistive film and thin copper, magnitude error below 0.25 dB and phase
error below 10 degrees; thick copper, magnitude error below 2.5 dB and
magnitude slope within 2 dB/decade of the 10 dB/decade skin-effect estimate.

The first run's four time-domain probe files are in
`conducting-sheet-probes.tar.gz`. `conducting-sheet-results.npz` contains the
frequency axis, reference field, and FDTD/analytic complex transmission
arrays and errors for all three sheet cases. Two cleanup-disabled captures,
using distinct output paths and an in-memory-only cleanup override, matched
bitwise in all numeric probe rows and derived complex response arrays. The
pinned source was not changed. `TRACE-SHA256SUMS` records the four source trace
hashes; `SHA256SUMS` verifies the compressed trace archive and result arrays.

The original-grid analytic errors were:

| Case | Maximum magnitude error | Maximum phase error | Source test result |
| --- | ---: | ---: | --- |
| Resistive film | 0.017 dB | 6.54 degrees | Pass |
| Thin copper | 0.099 dB | 3.84 degrees | Pass |
| Thick copper | 1.982 dB | 18.29 degrees | Pass; phase is not bounded |

The thick-copper magnitude slope was 8.8 dB/decade (analytic estimate:
10 dB/decade).

Five separately launched, cleanup-enabled test runs passed. Each run included
four solver calls and reached the same stopping-step counts. The 20 internal
solver times, in seconds and in run order, were:

```text
0.042648 0.035180 0.039101 0.032156
0.040521 0.030092 0.030240 0.031925
0.030106 0.027362 0.027478 0.029034
0.031993 0.028421 0.027302 0.028788
0.029203 0.028691 0.028899 0.028656
```

The range was 0.027302–0.042648 s (median 0.029648 s, mean 0.031390 s,
sample standard deviation 0.004501 s, coefficient of variation 14.34%).
Process peak RSS ranged from 86,608 to 86,928 KiB (median 86,696 KiB);
end-to-end wall time ranged from 0.38 to 0.72 s. These small, platform-specific
measurements characterize the case but are not performance thresholds.

A sensitivity probe changed only the axial grid spacing in memory. At
0.20 mm, all source assertions passed; maximum complex-response changes from
the 0.25 mm reference were 0.0093 dB / 1.614 degrees for the resistive film,
0.0153 dB / 0.278 degrees for thin copper, and 0.0052 dB / 0.033 degrees for
thick copper. A coarser aligned 0.50 mm grid converged but exceeded the
resistive-film phase bound at 12.39 degrees. A 0.30 mm grid did not align the
source/sheet/probe planes; it warned that the source primitive was unused and
did not converge, so it is not a valid sensitivity sample.

The source test's analytic limits are provisional candidate acceptance
bounds for Rust, not approved same-grid raw-field tolerances. The finer-grid
results support retaining those bounds without widening them; the coarse-grid
failure shows the result is resolution-sensitive. Final comparison criteria
remain subject to Task 15 review.

From the pinned repository root in the configured Python environment, rerun
the source assertions with:

```sh
python3 openEMS/python/Tests/Conducting_Sheet.py
```

The test deletes its output folders after each simulation. To preserve probe
outputs, use a distinct `Sim_Path` and disable cleanup in an in-memory
execution; do not edit the pinned source.
