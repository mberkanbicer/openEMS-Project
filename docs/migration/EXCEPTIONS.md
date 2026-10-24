# Exception register (RM-126)

Approved, bounded omissions from the native feature set. Every entry needs an
impact statement, an owner decision and a native-compatibility path. Anything
not listed here is an open task, not an accepted exception.

| ID | Exception | Decision | Impact | Compatibility path |
| --- | --- | --- | --- | --- |
| E-001 | fparser numeric variants (`float`, `long double`, long integer, MPFR/GMP) are not ported; only `f64` is maintained | ADR 0006 (D-06) | Scripts that rely on extended precision or MPFR/GMP evaluate in `f64`. The openEMS solver and CSXCAD use `f64` in the reference build, so solver results are unaffected | A consumer that needs another precision requires a new decision; the native C++ parser remains available for differential checks |
| E-002 | `ctb-rs` ships as a library plus the MATLAB/Octave delivery path; it has no standalone binary | RM-014 | There is no `ctb` command on `PATH`; the network transforms are reached through the library, the MEX layer or the CLI where applicable | Add a `[[bin]]` target if a command-line consumer appears; the install layout already reserves `bin/` |
| E-003 | The HDF5 field I/O requires the system HDF5 C library when the `hdf5` feature is enabled | ADR 0003 (D-03) | Builds without system HDF5 cannot write native field dumps; the feature reports `Hdf5Error::Unsupported` instead of writing a private format | Install the distribution's HDF5 development package (CI does this) or point `HDF5_LIB_DIR` at the library |
| E-004 | The GUI uses egui/wgpu instead of Qt/VTK | ADR 0004 (D-04) | Qt-specific extensions and VTK-backed dialogs are not available; exports are implemented in Rust | Native workflows are preserved at the model and file-format level; export parity is tracked by RM-104 |

## Change rule

An exception may only be added or removed together with the decision record it
cites. Removing an exception requires the missing capability to be implemented
and validated first.
