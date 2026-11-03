# XML, HDF5, VTK and Touchstone compatibility

## XML (CSXCAD / openEMS project format)

- 11 fixtures in `CSXCAD/rust/tests/fixtures/xml/` were written by the pinned
  native `ContinuousStructure::Write2XML` (every concrete property type,
  transforms, parameters, cylindrical, disc material, the openEMS wrapper).
  `xml_native_corpus.rs` reads and re-emits them.
- Attribute names, units, property order/priority and parameter expressions are
  preserved; no old attribute is renamed in place.
- `test_XML_RoundTrip` (carried native suite) passes after RM-168; `Write2XML`
  now refuses an incomplete setup (no CSX or no excitation) like native, and the
  DC-free Gaussian survives the round-trip.
- Precision: the XML writer is not forced to reproduce TinyXML1's historical
  double truncation; the round-trip is tested against native-written fixtures.

Evidence: `cargo test -p csxcad-core` (216 tests) + `test_XML_RoundTrip`.

## HDF5

- Feature-gated (`hdf5`), system C library (E-002). `Hid = i64`.
- Suites: 475 HDF5-feature tests (recorded acceptance); native layout for
  fields, probes, SAR and NF2FF; compound-complex and split real/imag readers.
- Field/probe datasets are compared per dataset by the differential harness
  (1 % RMS of the peak).
- The HDF5 writer is exercised by the Rust dumps consumed by the native
  `nf2ff` tool (RM-076).

## VTK

- `.vtr/.vts/.vtp` writers are compared **textually** by the reference harness.
- `--nativeFieldDumps` produces a `.vts` that matches native bit for bit on the
  closed cylindrical case (200 points, 0.0 difference, RM-144).
- **Gap:** no independent VTK reader (ParaView/VTK library) is used in CI; the
  comparison is against native bytes, not a third-party reader.

## Touchstone

- `CTB/rust/src/touchstone.rs` reads/writes `.sNp` with S/Y/Z/ABCD conversions
  and reference impedance renormalization; `CTB/rust/tests/differential.rs` and
  the Octave exercise cover the CLI.
- Format details tested: port count, frequency ordering, RI/MA/DB forms and
  reference impedance.
- **Gap:** no external (e.g. scikit-rf) reader cross-check.

## What is not claimed

- No corrupt-file fuzzing for XML/HDF5/Touchstone.
- No third-party tool import test for VTK.
- No backward corpus from older upstream releases beyond the 11 pinned
  fixtures.
