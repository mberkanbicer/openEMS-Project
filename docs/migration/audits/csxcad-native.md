# CSXCAD Native Model and XML Audit

**Status:** Native source audit complete for the pinned submodule; the later
WSL baseline passed the two registered native tests. Subclass-copy and full
XML differential validation remain open. No CSXCAD code has been changed.

## Scope and evidence

Initial source inspection covers `ContinuousStructure` XML persistence,
`CSBackgroundMaterial`, `CSPrimBox`, public structure methods, and the visible
native/Python XML test entry points. This is not yet a complete class/function
inventory or an executed compatibility baseline.

The native configure check was attempted with
`cmake -S CSXCAD -B <TEMP>\openems-csxcad-audit-build -DCMAKE_BUILD_TYPE=Release`
using Visual Studio 2022/MSVC 19.44. CMake found neither the fparser include
directory (its default `FPARSER_ROOT_DIR` was `/usr`) nor TinyXML's library
and include directory, and stopped at `find_package(TinyXML)`. No dependency
was installed. The C++ tests therefore could not be built or run in this
environment; the existing `CSXCAD\build\CTestTestfile.cmake` is absent.

## Source map

- `src/ContinuousStructure.h` exposes structure update/validation, grid edge
  insertion, object bounds, `clear`, and XML read/write overloads accepting
  TinyXML nodes or file paths. The class stores a raw `ParameterSet*`, grid,
  background material, and `std::vector<CSProperties*>`.
- `ContinuousStructure` initializes a `ParameterSet` with itself as owner and
  owns the grid and background material. Its destructor calls `clear()` and
  deletes the parameter set; the class documentation says destruction deletes
  all properties and primitives. `AddProperty` updates the property, stores
  it, assigns the structure as owner, and assigns a unique ID.
- Property removal has two distinct contracts: `RemoveProperty` erases the
  property and detaches its owner, handing ownership back to the caller;
  `DeleteProperty` deletes it. `DeletePrimitive` deletes the primitive and
  relies on the primitive to remove itself from its property. The full
  ownership graph and copy/assignment behavior across all subclasses remain
  untraced.
- The public structure API also exposes property/primitive lookup and
  enumeration, priority-based coordinate lookup, unused-primitive reporting,
  property status, grid-edge insertion, validity checks, and `Update()`.
  `GetPrimitivesByType` is declared but its inspected implementation prints
  “not yet implemented” and returns an empty vector; preserve this observable
  limitation unless an owner-approved behavior change is made.
- `src/ContinuousStructure.cpp` writes a `ContinuousStructure` element with
  coordinate-system attribute, rectilinear grid, background material,
  parameter set, and ordered property elements. `parameterised` and `sparse`
  are propagated to child serialization.
- `ReadFromXML` clears the current structure first, then reads the first
  `ContinuousStructure` child. Missing background material resets defaults;
  malformed background material returns an error string. Parameter-set parse
  failure appends a warning but continues. Missing `Properties` returns a
  warning string. Property tags dispatch to concrete property classes; legacy
  `ChargeBox` maps to `ProbeBox`, and both `DiscMaterial` and
  `Discrete-Material` map to discrete material. Unknown tags are written to
  stderr and skipped.
- `src/CSBackgroundMaterial.cpp` defaults relative permittivity and
  permeability to 1, and electric and magnetic conductivity to 0. Setters
  reject values below those limits by logging and retaining the previous
  value. XML attributes are optional and missing values retain defaults.
- `src/CSPrimBox.cpp` stores two parameterized coordinate vectors, evaluates
  and converts them during update, supports preserving or normalizing bounding
  box orientation, and serializes coordinates as `P1` and `P2` children.
  XML read requires both children.
- Public property families include unknown, material/dispersive/Lorentz/Debye,
  discrete material, lumped element, metal/conducting sheet, excitation,
  probe/dump/resistive boxes, and absorbing boundary condition. The base API
  provides type/name/ID/attribute access, copy creation, coordinate checks,
  primitive management, visibility/colors, and XML persistence.
- Primitive families declared by `CSPrimitives::PrimitiveType` include point,
  box/multibox, sphere/spherical shell, cylinder/cylindrical shell, polygon,
  linear/rotated polygon, polyhedron/polyhedron reader, curve, wire, and
  user-defined geometry. The base API includes coordinate-system and transform
  access, bounds, update/validity, property linkage, and XML persistence.
- `CSTransform` supplies primitive transforms; `CSRectGrid` supplies
  rectilinear mesh storage and edge operations; `Parameter` and `ParameterSet`
  provide named/evaluated values. Property coordinate parameters are managed
  by a separate parameter set. Exact behavior of every concrete subclass is
  not exhaustively enumerated here.
- Primitive transfer semantics are explicit in source: `SetProperty` removes
  the primitive from its prior property before assigning and adding it to the
  new one. Primitive destruction removes it from its current property and
  deletes its lazily created transform. This is why `ReplaceProperty` can
  repeatedly move the old property's first primitive until none remain.
  `CSProperties` copy construction shares the parent `ParameterSet*`; copying
  primitives is optional. These raw-pointer contracts and concrete subclass
  copy behavior are compatibility constraints.
- Visible tests include `tests/test_csobject.cpp`,
  `tests/test_csrectgrid.cpp`, and `python/tests/test_XML_RoundTrip.py`. The
  full registered test inventory and runtime coverage could not be checked
  because configure prerequisites are missing.

## Initial compatibility risks and open questions

1. **Global locale mutation:** file-based `ContinuousStructure::Write2XML`
   calls `setlocale(LC_NUMERIC, "en_US.UTF-8")` and does not restore the prior
   process locale. Verify portability and serialization behavior on supported
   platforms before deciding the Rust compatibility contract.
2. **Destructive/partial reads:** `ReadFromXML` calls `clear()` before checking
   the document root. Determine the resulting object state for malformed,
   missing, and partially valid sections, and whether callers rely on partial
   state after an error string is returned.
3. **Null XML node:** the node overload dereferences `rootNode` without an
   evident null check in the inspected code. Confirm whether null is excluded
   by API contract or is a caller-visible failure case.
4. **Ownership and lifetimes:** structure/property and parameter-set storage
   use raw pointers. Trace constructors, destructor, copy operations, and
   property/primitive removal before documenting ownership guarantees.
5. **Unsupported property tags:** unknown XML property types are logged and
   skipped rather than returned as an error. Establish whether read/write
   round-trip compatibility requires preserving unknown nodes.
6. **Validation limits:** background material setters log and ignore
   out-of-range values; verify behavior for NaN/infinity and for parameterized
   values after evaluation.

No defect is classified from this initial pass alone. The above are
source-supported compatibility questions; tests and broader source tracing
remain necessary.

## Native error-ordering facts (recorded for Rust parity)

These facts were verified against the native CSXCAD C++ source and are
required for Rust `parameter_update_errors()` parity:

- **PSErrorCode2Msg:** Codes -1, 0, 1-5, 100-110 have messages; every other
  code maps to an empty string (no `default:` case in the native switch).
- **Setter behavior:** Every native setter uses `Eval=true` and discards the
  returned error code; errors are consumed at set time, not deferred.
- **bModified:** Stays `true` from construction; no native code calls
  `SetModified(false)`.
- **MultiBox coordinate order:** Native evaluates per-axis across all boxes:
  for each axis (x, y, z), evaluate `start` then `stop` for all boxes —
  i.e., `box1.start.x, box1.stop.x, box1.start.y, box1.stop.y, box1.start.z,
  box1.stop.z`, then `box2.start.x, box2.stop.x`, etc. All coordinates are
  evaluated and all errors collected; no short-circuit.
- **Cylinder:** Native evaluates all coordinates (axis, radius, optional
  shell_width) and collects all errors; no short-circuit when axis fails.

## Remaining audit work

- Trace concrete subclass copy/assignment and ownership behavior in more
  detail before implementing their Rust equivalents.
- Complete XML tag/attribute coverage, legacy aliases, error/partial-state
  behavior, and round-trip cases with executable reference tests.
- Run the native C++ suite when fparser headers and TinyXML are available;
  this audit records source-level contracts, not runtime equivalence.
