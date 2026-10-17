# FieldProbes WSL Reference

This is a compact, lossless subset of one output set from the pinned
`openEMS/python/Tests/FieldProbes.py` analytic dipole test.

- Root repository: `974294ba7d812ef5a46a4760593057aee7ce6866`
- `openEMS` submodule: `305df56aa7df4d2f18c687083f484a96f9a22610`
- Input SHA-256: `ff43ec6ad34983dbe3cb12c2fb67c8cceb5a2659a571bca401a7c95ccc40c158`
- Environment: Ubuntu 26.04.1 under WSL, GCC/G++ 15.2.0, openEMS 0.37.0,
  Python 3.14.4, NumPy 2.3.5, HDF5 1.14.6; Intel Core i9-13900H, 20 logical
  CPUs
- Case: 41x41x41 cells (68,921 total), 10,000 timestep cap, 500 MHz probe and
  dump frequency, 23 VTK slices

`fieldprobes-selected.tar.gz` contains `Et.h5`, `Ht.h5`, `Ef.h5`, `Hf.h5`,
and all 22 numeric probe text files from the first run. The time-domain E/H
plane dumps contain 1,251 snapshots each. `fieldprobes-keyframes.npz`
contains losslessly compressed quarter-run frames for `Et_n`, `Dt_n`, `Ht_n`,
`Bt_n`, `Ht`, and `Bt`, along with each frame's time, mesh lines, and timestep
index. These selected artifacts retain full E/H plane histories and probe
traces plus the state used for the source test's D/E and B/H consistency
checks. Full-resolution histories for `Et_n`, `Dt_n`, `Ht_n`, `Bt_n`, and
`Bt`, plus the VTK slices, are not included.

The complete first output set contained 54 files (119 MiB). Its SHA-256
manifest is `run-1-SHA256SUMS`; it documents the full original output set,
including files not kept here. `artifact-SHA256SUMS` covers the archive and
keyframe file. Repeated runs matched all 9 HDF5 files and 22 numeric text
files bitwise; the repeated output set was cleaned after comparison.

All eight runs passed the source test's assertions: TD probe/dump agreement
(relative error below `1e-6`), free-space D/E and B/H checks (below `1e-5`),
FD checks (below 1% and `1e-5`), rotational symmetry (below `1e-5`), analytic
Hertzian-dipole ratios (below 10%), and nonempty VTK output. Observed relative
differences were `D - eps0*E = 6.29e-9`, `B - mue0*H = 5.30e-8`, and
non-interpolated `B - mue0*H = 3.05e-8`; analytic E/H ratio errors were 5.07%
and 4.18%. The simulation did not reach its -60 dB end criterion before the
10,000-step cap. These source-test criteria are not approved Rust migration
tolerances and the capped case is not a converged scientific reference.

Three cleanup-enabled repeats recorded solver times of 9.61, 8.60, and 8.63 s
(median 8.63 s, mean 8.94667 s, sample standard deviation 0.5747 s,
coefficient of variation 6.42%). The internal solver timer excludes
post-processing and cleanup. Three more process-isolated runs all passed and
recorded peak RSS of 121,788, 122,248, and 122,920 KiB (median 122,248 KiB);
their end-to-end elapsed times were 11.73, 11.50, and 11.25 s. The peak RSS
includes the Python process, native solver, dumps, and post-processing; wall
time includes startup and cleanup. These are capped-case measurements only,
not a converged-case performance or memory threshold.

From the pinned repository root in the configured Python environment, rerun
the source assertions with:

```sh
python3 openEMS/python/Tests/FieldProbes.py
```

To preserve outputs, use a distinct `Sim_Path` and disable cleanup in the
in-memory test execution; do not edit the pinned source. The source's default
cleanup removes its output directory after the run.
