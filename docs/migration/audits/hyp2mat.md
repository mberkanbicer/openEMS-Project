# hyp2mat Parser and Conversion Audit

**Status:** Source and repository-fixture audit complete for the pinned
submodule. No hyp2mat code was changed; native conversion behavior remains
unvalidated because the build prerequisites and a HyperLynx input fixture are
unavailable in this checkout.

## Source map

- `lib/scan.ll` tokenizes HyperLynx text and `lib/parse.yy` defines the Bison
  grammar. Grammar actions populate `parse_param` records and dispatch into
  `HypFile::Hyp::exec_*` handlers.
- `lib/hypfile.{h,cc}` owns parser state and input loading. `Hyp::load` calls
  `yyparse`, then closes `yyin`; `lib/hyperlynx.{h,cc}` transfers the parsed
  model into the public PCB representation.
- `lib/hyp2mat.h` defines the PCB, stackup/layer, polygon, via, device, pin,
  and network-related model types. The `exec_*` handlers are split by board,
  stackup, device, padstack, net, polygon, and net-class records.
- `src/hyp2mat.cc` is the CLI dispatcher. `src/cmdline.ggo` declares the input,
  output, and `csxcad`, `pdf`, and `qucs` output-format choices.
- `lib/csxcad.cc`, `lib/pdf.cc`, and `lib/qucsstudio.cc` implement the three
  output paths. `matlab/ImportHyperLynx.m` invokes the CLI and evaluates its
  generated MATLAB script; neighboring M-files provide port lookup and
  material helpers.

## Input and model coverage

The grammar includes board-file metadata, format version, data mode, units,
plane separation, perimeter segments/arcs, board attributes, signal and
dielectric stackup records, planes, devices, supplies, padstacks, nets,
segments/arcs, vias, pins, pads, usegments, polygons, polygon voids, polylines,
net attributes/classes, keys, and end records. The parser carries English
versus metric units and copper-thickness units; the PCB model documents its
lengths in meters.

This is a grammar for the HyperLynx/`.hyp` input dialect, not a general PCB
exchange parser. The README also claims QucsStudio PCB input, but the audited
CLI/parser exposes HyperLynx input and the QucsStudio code exposes a writer
only. Treat the README/code difference as an unresolved compatibility
question, not a verified defect.

## Output behavior

- **CSXCAD:** Emits a MATLAB script describing board dielectric/cutouts,
  copper layers, vias, and device/port metadata. Copper can be exported as
  2D polygons or 3D linear polygons, and optional lossy copper uses layer
  resistivity. Pin ports are represented by axis-aligned bounding boxes.
- **PDF:** Uses the libhpdf-backed renderer for printable board output.
- **QucsStudio:** Writes a QucsStudio layout with board, copper, vias,
  devices, and ports. The exporter writes the first stackup layer and warns
  when additional layers are present; multilayer conversion is therefore not
  preserved by this output path.

The CLI option specification defaults the output format to PDF and the output
path to `-`. The MATLAB importer explicitly selects CSXCAD output and writes
`pcb.m`, then runs that script. The wrapper also advertises a `version`
argument and constructs a `--version` option, but the checked-in CLI option
specification does not declare it; confirm generated CLI behavior before
freezing that wrapper contract. The wrapper builds a shell command from the
filename and optional arguments and uses `system`; its quoting and failure
behavior have not been exercised.

## Fixtures, dependencies, and validation

- The repository contains Eagle `.brd` tutorial/demo files and Eagle-to-Hyp
  workflow examples, but no `.hyp` input fixture was found.
- No test-named files were found under `hyp2mat/`.
- The Windows host has no `autoreconf`, `autoconf`, `automake`, `make`, Bison,
  Yacc, Flex, or gengetopt command available on `PATH`. The autotools build
  and generated parser therefore could not be run. No dependency was installed.
- No CLI conversion, MATLAB import, PDF, or QucsStudio output was executed.
  Parser error handling, malformed-input behavior, numeric conversion,
  exporter geometry, and output validity still need reference tests.

## Remaining compatibility work

- Obtain or create a legally usable HyperLynx fixture and run the original
  converter and MATLAB import workflow in a supported build environment.
- Resolve the README's QucsStudio-input claim and the MATLAB wrapper's
  `--version` option against the original executable.
- Add differential checks for parser errors, units, board geometry, all output
  formats, multilayer behavior, and exporter handling of missing/empty model
  sections before setting Rust acceptance criteria.
