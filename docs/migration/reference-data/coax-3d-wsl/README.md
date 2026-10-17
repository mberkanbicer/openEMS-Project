# Converged 3D coax reference

Captured from the pinned `openEMS/python/Tests/Coax.py` source, SHA-256
`36bd99d99bf8419a0eb195214e502ce6922d9606baca986c4bd5286368b08008`.
The source was not changed. For capture, the simulation output path was
redirected to each run folder, cleanup was disabled, and the calculated port
and S-parameter arrays were saved as NPZ files.

The case uses openEMS 0.37.0 in the documented Ubuntu 26.04.1 WSL baseline
(Python 3.14.4, HDF5 1.14.6). Its 150 mm coax model uses a 97x97x76 mesh
(715,084 cells), 0.25 mm transverse spacing, 2 mm axial spacing, and a
1-3 GHz sweep with 201 points. Both runs reached the configured `EndCriteria`
after 2,264 timesteps at -51.31 dB and passed the original script assertions.

The analytic coax impedance is 49.939974651068 ohms. The maximum numerical
impedance error was 1.20%; maximum S11 was -50.8824 dB, and S21 ranged from
-0.0081 to +0.0034 dB. Solver times were 11.33 and 12.03 seconds. These are
platform-specific characterization measurements, not acceptance limits.

`run1-ports.npz` and `run2-ports.npz` are each 40,230 bytes and have identical
SHA-256 `76c83b36eccb3238e3eec9c1eb0b8a10586a8ea0e4ad83a6548496a270a9922d`.
They contain `freq`, `s11`, `s21`, `s11_dB`, `s21_dB`, and each port's
incident/reflected/total voltage, reference impedance, and accepted power.
The E/H HDF5 files are identical across runs: `et` is SHA-256
`8a0cc2df705c4185e1877f32183a0c62b1dff263976ad9341c4d6c9969ae5ef8`, and
`ht` is SHA-256
`3b376ca042c2009eb2f99ce882f29100224aaee9246fe62788b8b2d18d17bcfd`.
Numeric rows of all ten port text files also match; their timestamp comment
headers differ.

The `run1/Coax/` and `run2/Coax/` directories retain the original solver
outputs, including both HDF5 files and the port text files. The exact
capture method and measured results are recorded in
`docs/migration/VALIDATION.md`.
