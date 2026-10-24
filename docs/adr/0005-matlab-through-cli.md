# ADR 0005 - MATLAB and Octave through the CLI first

- **Status:** Accepted
- **Date:** 2026-10-24
- **Decision owner:** Project owner
- **Related:** D-05, RM-083, RM-091, RM-092

## Context

The native MATLAB/Octave layer is a set of M-files that write CSXCAD XML and
launch the `openEMS` binary, then read the HDF5 output. Reimplementing the whole
layer as MEX calls before the binary contract works would invert the dependency:
the M-files are also the primary acceptance test for the CLI.

## Decision

Make the Rust CLI accept the native invocation contract
(`openEMS <FDTD_XML_FILE> [options]`) first. Then run the existing M-files
unchanged against the Rust binary, and only afterwards add MEX entry points for
the parts that cannot go through the CLI.

## Consequences

- The M-files stay unmodified where possible; that is the compatibility test.
- RM-083/RM-084 gate RM-091/RM-092.
- The C ABI crates (`openems-matlab`, `csxcad-matlab`) are installed for the
  parts that need in-process access.
