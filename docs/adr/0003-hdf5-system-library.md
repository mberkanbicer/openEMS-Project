# ADR 0003 - HDF5 through the system C library

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-03, RM-076, RM-077

## Context

openEMS writes HDF5 field dumps that Octave and MATLAB read directly. Two
options exist: a pure-Rust HDF5 implementation or FFI to the system HDF5 C
library. The file layout must match the native writer byte-for-byte in dataset
names, shapes, attributes and ordering.

## Decision

Use the system HDF5 C library through a feature-gated FFI module
(`openems-core` feature `hdf5`, `build.rs` honouring `HDF5_LIB_DIR` or
`pkg-config`). Without the feature the API returns an explicit
`Hdf5Error::Unsupported`; no private substitute format is written.

## Consequences

- The HDF5 backend is an optional build dependency; the default build stays
  dependency-free.
- CI installs `libhdf5-dev` for the `hdf5` job.
- The native `hdf5.dll` on Windows needs an import library; the procedure is
  recorded in `VALIDATION.md`.
- The layout is verified by reading a recorded native dump; a native-reader
  acceptance test remains open (RM-076).
