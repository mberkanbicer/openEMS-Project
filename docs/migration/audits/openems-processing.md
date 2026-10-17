# openEMS Processing, I/O, NF2FF, SAR, and Tools Audit

**Status:** Source-path and format map complete. Principal native-backed
Python/Octave suites passed in the later WSL baseline. Repeated capped-smoke
time traces and HDF5 E/H plane snapshots are preserved and numerically
identical; broader format/scale round trips and Rust differential checks
remain open. No openEMS code was changed.

## Processing and field access

`Common/processing.h` defines a common sampling lifecycle (`PreProcess`,
`Process`, `PostProcess`) with enable state, time-step intervals, explicit
sample steps, start/stop times, frequency sampling, flush controls, precision,
and main/dual mesh/time options. `ProcessingArray` owns and schedules
processing objects. Each processing uses its own
`Engine_Interface_Base`, which exposes interpolated E/H/J/rot(H)/D/B samples,
voltage integrals, time/timestep access, and a fast approximate total-energy
estimate. The engine interface supports no, node, and cell interpolation.

## HDF5 and VTK

The I/O implementation is grouped under `tools/hdf5_file_reader.*`,
`tools/hdf5_file_writer.*`, and `tools/vtk_file_writer.*`, with processing
implementations under `Common/processfields*` and MATLAB conversion support
in `matlab/ConvertHDF5_VTK.m`.

`ProcessFieldsFD` accumulates each frequency in a complex-float array using
the sampled field, `exp(-j 2 pi f t)`, a factor of 2 for the single-sided
spectrum, and `dt * FD_interval`. HDF5 output is placed under
`/FieldData/FD`; frequencies are stored as metadata and fields are written as
`f0`, `f1`, etc. Legacy output splits real and imaginary parts and associates
frequency metadata with each. VTK output writes 21 phase snapshots per
frequency plus magnitude and argument files, with frequency encoded in the
filename. Exact time-domain dataset names, all field-unit conventions, and
reader/writer round-trip behavior still need reconciliation across dump types.

## NF2FF and SAR

NF2FF is a separate post-processing library (`nf2ff/`) that consumes dumped
near-field E/H data. Its interface/implementation are in `nf2ff/nf2ff.*` and
`nf2ff/nf2ff_calc.*`; Matlab entry points include `CalcNF2FF.m` and
`AnalyzeNF2FF.m`, and Python support is in `python/openEMS/nf2ff.py` plus
`_nf2ff.pyx`. The solver suite includes `combinedtests/nf2ff_dipole.m`.

SAR processing is implemented by `Common/processfields_sar.*` and
`tools/sar_calculation.*`, with Python helpers/binding in
`python/openEMS/sar_utils.py` and `sar_calculation.pyx`. It frequency-accumulates
E fields and optionally J fields; its default uses cell conductivity. It
requires cell interpolation, rejects raw-data output unless the file type is
HDF5, and ignores subsampling requests with a warning. It builds per-cell
volume, density, and conductivity data from material properties and warns
that anisotropic material is unsupported. The exposed dump types are local,
1 g, 10 g, and raw-data SAR. Exact averaging, normalization, and output-unit
contracts require formula-level differential tests.

## Existing test and reference coverage

The Octave/Matlab suite includes `probes/fieldprobes` and
`combinedtests/nf2ff_dipole`; the later WSL baseline passed the 10-case
Octave/Matlab suite. Python coverage includes
`python/Tests/test_hdf5_utils.py` and `python/Tests/test_sar_analytic.py`;
both ran in the 31/31 WSL Python unit/simulation suite. The standalone Python
FieldProbes analytic test and the Octave/Matlab probes passed their assertions,
but the FieldProbes run reached its timestep cap. Native NF2FF solver cases,
broader I/O format/scale round trips, and full differential references remain
open.

## Remaining compatibility work

- Trace time-domain HDF5 dataset layout, VTK mesh/field ordering, legacy dump
  behavior, units, scaling, and reader/writer round trips.
- Compare NF2FF integration/sign/coordinate conventions and far-field outputs
  against the dipole reference.
- Trace SAR formulas, averaging kernels, density/conductivity assumptions,
  normalization, units, and all output dump types against analytic cases.
- Add path-specific native and Python processing tests beyond the principal
  suites; save exact inputs, files, comparisons, and tolerances.
