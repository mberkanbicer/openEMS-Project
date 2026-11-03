# hyp2mat Parser and Conversion Audit

**Status:** Source and repository-fixture audit complete for the pinned
submodule. No native hyp2mat code was changed.

> **Port status (2026-10-27):** superseded by the Rust port. The converter,
> its writers and its CLI are implemented in `hyp2mat/rust` and verified
> against a native 0.0.18 build; the evidence is in
> `docs/migration/VALIDATION.md` (RM-107..RM-111) and in the section at the end
> of this file. The audit below records the original findings, including the
> items that were later confirmed or resolved.

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

## Port and verification (2026-10-27)

The port lives in `hyp2mat/rust`: `hypfile.rs` (native model, units, stackup,
padstacks, board edge, arcs/segments, flood), `parser.rs` (Flex/Bison-faithful
lexer and recursive-descent parser with the native error recovery), `pcb.rs`
(copper/plane/via/pin assembly, crop, overrides, summary and net printing),
`polygon.rs` (stateful native `Polygon` with a Rust port of Clipper 1's offset
builder and booleans), `csxcad.rs` (native MATLAB writer plus CSXCAD XML through
`csxcad-core`), `qucsstudio.rs`, `pdf.rs`, `format.rs` (C++ `%g`) and `cli.rs`
(the full native option set, installed as `hyp2mat`).

Evidence recorded in `VALIDATION.md` and `tests/reference/README.md`:

| Check | Result |
| --- | --- |
| Fixture corpus | 9 `.hyp` files (3 native EAGLE examples, 6 grammar-derived), SHA-256 manifest, provenance README |
| Native model dump (`-d`) | byte-identical for 9/9 |
| Native `--raw` polygons | byte-identical for 4/4 fixtures including arcs |
| Native `-v` board/layer summary | byte-identical for 9/9 (native writes it to stderr) |
| CSXCAD script | non-polygon lines byte-identical; geometry exact for 7/9; <= one 10 um grid step on the two arc fixtures; copper area <= 1.7e-3 relative |
| Native CSXCAD reads the Rust XML | all 9 documents load and the model dump is identical to the Rust dump (255 lines) |
| QucsStudio | properties exact, items within the same bound, identical stderr multiset |
| PDF | real multi-page PDF, Ghostscript 10.06 renders 3/3/3/3/4/3/3/5/3 pages |
| Determinism | 5 output variants x 9 fixtures, all byte-identical across runs |
| Tests | 114 (77 lib + 23 CLI + 14 fixture), fmt and clippy clean |

Preserved native quirks: `{UNITS=METRIC}` means centimetres, the imperial
copper-weight thickness is 1000x (native defect), `VAL=` is always a string, a
deprecated `PAD` yields a zero-size pad, the plane-mask filter uses the target
net name, a syntax error exits 0, and `-f pdf` without `-o` prints
`pdf output file missing` and writes nothing.

Deviations: the additive `--csxcad-xml` output is new (`-f csxcad` keeps the
native MATLAB script); the Clipper2 backend resolves one shallow arc
intersection one 10 um grid step away from Clipper 1 in two fixtures (bound and
approval status in `REFERENCE_TOLERANCES.md`); flood without a board outline is
an error where native segfaults; `-d` levels 2-4 do not reproduce Flex/Bison
tracing, but the `-d` model dump is byte-identical.
