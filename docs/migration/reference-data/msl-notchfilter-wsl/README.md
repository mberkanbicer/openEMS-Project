# MSL Notch Filter WSL Reference

This directory contains raw outputs from two identical runs of the pinned
Python MSL Notch Filter smoke test:

- Root repository: `974294ba7d812ef5a46a4760593057aee7ce6866`
- `openEMS` submodule: `305df56aa7df4d2f18c687083f484a96f9a22610`
- Input: `openEMS/.github/smoketests/python/MSL_NotchFilter.py`
- Input script SHA-256:
  `3293542c4a4b2724786588c2b485110719ca883aa83c9d3969b11b1876028765`
- Environment: Ubuntu 26.04.1 under WSL; GCC 15.2.0; openEMS 0.37.0;
  Python 3.14.4; NumPy 2.3.5; Intel Core i9-13900H, 20 logical CPUs
- Case: 269,780 cells, 1,000 timesteps, 7 GHz maximum excitation/frequency
- Output directories: `run-1/` and `run-2/` contain the 12 solver text files;
  `field-run-1/` and `field-run-2/` contain HDF5 E/H snapshots
- Root build command:
  `./update_openEMS.sh /home/mberkanbicer/opt/openEMS --python --python-venv-mode=disable --python-use-network=disable --with-CTB --njobs=4`

The source smoke test normally uses `cleanup=True`. For reference capture only,
the Python source was executed in memory with the output directory changed and
`cleanup=False`; neither the pinned test nor project source was modified.
For the field-state runs, two HDF5 dump objects were additionally added in
memory: E and H, raw time-domain mode, HDF5, subsampling `[4,4,1]`, on a
`[-1200,1200] x [-1200,1200] x {127}` micrometre plane. Each file contains
10 snapshots at timestep indices 0, 102, ..., 918. The E datasets have shape
`(3,5,5,1)` and H datasets have shape `(3,4,4,1)`, reflecting the different
Yee-grid layouts. Adding these dumps did not change any of the 12 original
smoke trace numeric arrays.
The simulation warned that 1,000 timesteps ended before the -60 dB criterion
and emitted invalid-division warnings during port post-processing. Treat this
as a capped, deterministic smoke reference, not as a converged physical
solution or a Rust acceptance threshold.

The numeric rows in all 12 files were identical across the two stored runs
(maximum absolute and relative difference: 0). All HDF5 dataset arrays and
attributes in both field-state runs also matched exactly. Port-file comment
headers include their generation timestamp and therefore differ. Five solver-time
measurements were 1.97905, 1.99594, 2.00918, 2.02864, and 1.97494 s (minimum
1.97494 s, median 1.99594 s, mean 1.99755 s, sample standard deviation
0.02212 s, coefficient of variation 1.11%). The first two runs preserved
outputs; the remaining three used the test's normal cleanup behavior. The
solver's internal timer excludes post-processing and cleanup. These
measurements are preliminary and are not a performance acceptance baseline:
this is one capped smoke case on one host. SHA-256 hashes are in
`SHA256SUMS`; each text-output run occupies 51,107 bytes, and each
field-state run occupies 144,856 bytes.

Reproduce with the pinned source and equivalent installed toolchain by running
the test with cleanup disabled and a distinct `Sim_Path`. Compare numeric data
rows, ignoring `%` comment headers. Hashes and exact byte sizes for the stored
files are recorded in `SHA256SUMS`.
