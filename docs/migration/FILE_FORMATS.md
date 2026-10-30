# File formats and compatibility guarantees (RM-082)

This document records the on-disk formats the Rust migration reads and writes,
and what "compatible" means for each of them. It complements
`VALIDATION.md`, which records the numeric evidence.

## 1. CSXCAD XML

The Rust workspace reads the native CSXCAD `ContinuousStructure` XML through
`csxcad_core::model::Structure::from_xml_str` and writes it through
`csxcad_core::serialization`.

Preserved structures:

- `<ContinuousStructure CoordSystem=…>` with `RectilinearGrid`,
  `XLines`/`YLines`/`ZLines`, `DeltaUnit` and the `DeltaUnit` scaling.
- All primitive kinds (`Box`, `Sphere`, `SphericalShell`, `Cylinder`,
  `Curve`, `Polygon`, `LinPoly`, `RotPoly`, `Polyhedron`, `MultiBox`,
  `UserDefined`, `PolyhedronReader`), their `Priority`, `Transform` children
  and the parameter expressions.
- Property kinds `Material`, `Metal`, `Excitation`, `ProbeBox`, `DumpBox`,
  `DebyeMaterial`, `LorentzMaterial`, `DiscreteMaterial`,
  `ConductingSheet`, `LumpedElement`, `AbsorbingBoundary`, `ResolutionBox`.
- Per-direction vectors (`Epsilon="2,4,6"`), the `Weight` child, `Isotropy`,
  and the `Property` child that carries both the base material values and the
  dispersive pole parameters.
- Probe/dump attributes: `Type`, `Number`, `NormDir`, `Weight`, `StartTime`,
  `StopTime`, `OverSampling`, `FD_Samples`, `DumpType`, `DumpMode`,
  `FileType`, `SubSampling`, `OptResolution`, `MultiGridLevel`, `Cylinder`.

Compatibility rules:

- Unknown attributes are preserved on write (the `attributes` list) and do
  not fail the parse.
- Missing optional attributes take the native defaults (for example
  `Caps="1"` for lumped elements, `Isotropy="1"` for materials, `Delay="0"`
  for excitations).
- A single vector value is replicated across the three components, exactly
  like native `ReadVectorTerm`; a two- or three-value vector fills the
  remaining components with the native default.
- Cylindrical `CoordSystem="1"` is a supported *parse* target but the Rust
  operator rejects it with a clear error until the cylindrical operators are
  ported (ADR 0002); it is never silently treated as Cartesian.

## 2. HDF5 field dumps

The native openEMS dump layout is reproduced by
`openEMS/rust/src/hdf5.rs` (system HDF5 through the `hdf5` feature) and
`processing.rs`.

Root

| Object | Type | Meaning |
| --- | --- | --- |
| `/Mesh/x`, `/Mesh/y`, `/Mesh/z` | `f64[]` | mesh lines in metres |
| `/Mesh` attributes | | `mesh_type` (0 cartesian), `mesh_scaling` |
| `/FieldData/TD/<8 digits>` | `f32[3, nx, ny, nz]` | time-domain snapshots |
| `/FieldData/FD/<name>` | complex `f32` datasets | frequency-domain dumps |
| root attributes | | `openEMS_HDF5_version`, `dump_type`, `dual_mesh`, `legacy_fmt` |

Dataset attributes:

- `d_order` — component order string (`NZYX` for the native dumps).
- `NXYZ` — mesh extents.
- `frequency` — `f32[]` on the `/FieldData/FD` group (one entry per dumped
  frequency).
- `TD` entries are named by the zero-padded timestep (native 8 digits).

Compatibility guarantees:

- A file written by the Rust writer is readable by the native
  `HDF5Dump`/`nf2ff` readers: same group names, dataset names, shapes,
  component order and attribute types.
- A file produced by the native solver is readable by `Hdf5File`; this is
  checked against the captured native reference
  `docs/migration/reference-data/msl-notchfilter-wsl/field-run-1/Et_ref.h5`
  (`native_reader_tests::reads_a_native_openems_dump`).
- `FDTD_FLOAT` is `f32` on both sides; complex dumps store real and
  imaginary parts as `f32` with the native compound layout.
- No private fallback format is written. If the `hdf5` feature is disabled
  the HDF5 writer is absent rather than silently substituting another format
  (ADR 0003).

## 3. Probe and port text files

`ProcessIntegral` and the field probes write the native text layout:

- comment header starting with `#`,
- one row per processed timestep: `time <value…>`,
- the frequency-domain companion `<filename>_FD` with one row per frequency
  and the complex values.

The DFT accumulation (`2 * dt * interval`, single-sided spectrum) and the
frequency rows follow `ProcessFieldsFD`/`ProcessIntegral`.

## 4. SAR dumps

The SAR calculation keeps the native quantities:

- local power density `0.5 σ |E|²` (W/m³) and local SAR (W/kg),
- 1 g / 10 g averages from the native cubical-mass search,
- the same cell width, cell volume and cell density inputs.

The raw SAR data group uses `Conductivity`, `Density` and `Volume` under
`/CellData` and the field datasets under `/FieldData/SAR`.
