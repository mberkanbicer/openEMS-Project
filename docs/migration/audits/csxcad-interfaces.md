# CSXCAD Python/Cython and Matlab/Octave Interface Audit

**Status:** High-level source map and callable inventory are in place; the
per-method contract audit remains incomplete. The later WSL baseline passed
150 CSXCAD Python tests (one skipped); Octave-specific XML writer edge cases
and many individual method contracts remain unvalidated. No CSXCAD source was
changed.

Per-method notes below that say the Python extension or Octave was unavailable
refer to the initial audit environment; the later suite results supersede
those environment-wide statements, but not untested individual contracts.

## Python/Cython surface

The Python package is installed from `CSXCAD/python` after the native library
is built and installed. Cython implementation/declaration modules cover
`ContinuousStructure`, properties, primitives, the rectilinear grid,
transforms, and parameter objects (`.pyx`/`.pxd`). Generated Cython `.cpp`
files are build products and are not source-of-truth. The package initializer
sets the Windows DLL search path from `CSXCAD_INSTALL_PATH` or
`OPENEMS_INSTALL_PATH`, resolves package metadata with a fallback version, and
exports `ContinuousStructure`.

Bindings wrap native pointers rather than copying their full object graphs.
`AddProperty`, `AddPrimitive`, and `SetTransform` transfer ownership to C++;
Python wrappers are borrowing handles. `CSTransform.fromPtr` and the
primitive/property wrappers retain one live wrapper per native pointer, so
retrieving an object again preserves Python identity. `no_init` creates a
wrapper shell for an existing pointer. Destruction callbacks invalidate such
wrappers when C++ destroys the object, and accessing a deleted primitive
raises `RuntimeError`. Parent-owned objects cannot necessarily be directly
constructed; for example, `CSBackgroundMaterial` is obtained from its
structure. `AddProperty` returns `None`.

The primitive factory explicitly raises for `USERDEFINED` primitives because
that wrapper type is not implemented; unknown primitive types and unsupported
keyword arguments raise exceptions. These are observable compatibility
boundaries, not porting defaults to silently replace.

### Structure-level input and ownership behavior

`ContinuousStructure.Write2XML` accepts `Path` or `str`, converts through
`pathlib.Path`, and raises `FileNotFoundError` when the parent directory is
absent; `ReadFromXML` passes a UTF-8 encoded filename directly to the native
reader. `DefineGrid` clears the existing mesh first, optionally smooths the
provided mesh mapping, sets each direction's lines, then applies the drawing
unit. `SetMeshType` updates both the grid and structure coordinate-input type.
`GetProperty` checks bounds and raises `IndexError`, while
`GetPropertyByCoordPriority` copies exactly three coordinates into a native
buffer. These conversions/checks should be preserved rather than inferred
from the native API alone.

`AddProperty` and `RemoveProperty` update the Python wrapper's resolved owner
after the corresponding C++ ownership operation; `DeleteProperty` delegates
deletion to C++ and relies on the wrapper invalidation path. Convenience
property constructors all route through `__CreateProperty`; only `AddMaterial`
explicitly checks that `name` is a Python `str` before dispatch. These are
source-level contracts, not all independently exercised in this environment.

### ContinuousStructure method contracts

| Method / group | Source-level contract |
| --- | --- |
| Constructor | Creates/owns a native structure unless `no_init=True`; accepts `CoordSystem` or `cs_type`; unknown keywords raise generic `Exception`. `__cinit__` receives variadic positional arguments but does not inspect them; their end-to-end construction behavior was not runtime-verified. |
| `Update`, `Clear` / `Reset` | `Update` decodes the native diagnostic as UTF-8; `Reset` aliases `Clear`. |
| `Write2XML(file)` / `ReadFromXML(fn)` | Writer converts `Path`/`str` with `Path`, requires the parent directory to exist, and passes an encoded path to C++; reader directly calls `fn.encode('UTF-8')` and decodes the native result, so a `Path` object is not accepted by the same conversion path. |
| `GetParameterSet`, `GetGrid`, `GetBackgroundMaterial`, `grid` | Retrieve stable cached wrappers for structure-owned members; `grid` aliases `GetGrid`. |
| `SetMeshType` / `GetCoordInputType` | Setter updates both grid mesh type and structure coordinate-input type; getter reads the latter. |
| `DefineGrid(mesh, unit, smooth_mesh_res=None)` | Clears the grid, optionally replaces each `mesh[k]` with its smoothed result (mutating the caller's mapping), replaces each direction's lines, sets drawing unit, and returns the same grid wrapper. |
| Property/primitive counts | `GetQtyProperties` and `GetQtyPrimitives(prop_type=ANY)` forward counts to native code. |
| `AddMaterial`, `AddDiscMaterial`, `AddAbsorbingBC`, `AddLumpedElement`, `AddMetal`, `AddConductingSheet`, `AddExcitation`, `AddProbe`, `AddDump` | Dispatch through `__CreateProperty`, set the name, add the property, and return its wrapper. Only `AddMaterial` and `AddMetal` annotate `name` as `str`; `AddMaterial` explicitly checks `isinstance(name, str)`, while the others rely on downstream conversion. `AddExcitation` and `AddProbe` also forward their required type/value arguments. |
| `AddProperty` / `RemoveProperty` / `DeleteProperty` | Add and remove transfer native ownership and refresh the Python `_owner`; delete destroys the property and uses the C++ destruction callback. |
| `GetProperty(index)` / `GetAllProperties()` | Indexed access checks negative and upper bounds and raises `IndexError`; list access wraps every native property in order. |
| `GetPropertiesByName(name)` / `GetPropertyByType(prop_type)` | Name input is UTF-8 encoded; both return lists of cached property wrappers. Type is Cython-converted to the native `PropertyType`. |
| `GetPropertyByCoordPriority(coord, prop_type=ANY, markFoundAsUsed=False)` | Copies the first three indexed coordinates into native doubles and returns only the winning property wrapper (the native primitive out-parameter is not exposed); the optional flag is forwarded to mark the found primitive used. |
| `GetAllPrimitives(sort=False, prop_type=ANY)` | Forwards sort and property type; returns a Python list of wrapped native primitives. |

The background-material wrapper is structure-owned and cannot be instantiated
directly. `GetEpsilon` / `SetEpsilon`, `GetMue` / `SetMue`, `GetKappa` /
`SetKappa`, and `GetSigma` / `SetSigma` forward directly to C++; `Reset`
restores vacuum defaults. Visible `test_CSXCAD.py` covers property
ownership and lookups, priority queries/used marking, reset, XML write/read,
grid identity/type, grid definition/smoothing, removal/deletion, and
type-filtered primitive collection. XML round-trip tests cover structure
serialization details and background-material defaults/reset/direct-
instantiation rejection; these test modules ran in the later WSL suite. The
writer/reader path asymmetry, uninspected positional constructor arguments,
and `DefineGrid` input-mapping mutation remain source-only.

The writer/reader path-type asymmetry, uninspected positional constructor
arguments, and `DefineGrid` input-mapping mutation are source-level
compatibility details; they were not runtime-probed. Do not infer that the
reader accepts `Path` because the writer does, or that grid smoothing preserves
its input mapping.

### Callable inventory

The source declaration scan found the following Cython `def` counts; counts
include constructors, private helpers, and special methods, so they are not
public API counts:

| Module | Declarations | Surface |
| --- | ---: | --- |
| `CSXCAD.pyx` | 48 | Background material and structure lifecycle, XML, grid, property/primitive creation and lookup |
| `CSProperties.pyx` | 174 | Property base, material models, excitations, probes, dumps, dispersive and discrete materials |
| `CSPrimitives.pyx` | 96 | Primitive base and point/box/cylinder/shell/sphere/polygon/curve/wire/polyhedron/multibox families |
| `CSRectGrid.pyx` | 19 | Mesh lines, sorting, smoothing, snapping, units, simulation area and validity |
| `CSTransform.pyx` | 16 | Matrix composition, transform application, translation, rotation and scale |
| `ParameterObjects.pyx` | 3 | Wrapper construction, address lookup and destruction |
| `Utilities.pyx` | 4 | Direction and coordinate utility functions |

A separate scan of Python-visible `def`/`cpdef` declarations finds 293
non-private declarations (256 distinct names) across these modules; every
distinct name is represented in the interface contracts above. C-level
`cdef`, underscore-prefixed helpers, and special methods are excluded from
this public-name count.

The Matlab public directory contains 58 M-files, with 12 additional files in
`private/`. Public entry-point families include `InitCSX`, `DefineRectGrid`,
`SetBackgroundMaterial`, `SetMaterialProperty`, `SetMaterialWeight`,
`SetExcitationWeight`, `SetExcitationWeightFile`; primitive/property creation
(`AddBox`, `AddConductingSheet`, `AddCurve`, `AddCylinder`,
`AddCylindricalShell`, `AddDebyeMaterial`, `AddDiscMaterial`,
`AddDjordjevicSarkarMaterial`, `AddDump`, `AddExcitation`, `AddLinPoly`,
`AddLorentzMaterial`, `AddLumpedElement`, `AddMaterial`, `AddMetal`,
`AddPlaneWaveExcite`, `AddPoint`, `AddPolygon`, `AddPolyhedron`, `AddProbe`,
`AddPropAttribute`, `AddRotPoly`, `AddSphere`, `AddSphericalShell`, and
`AddWire`); mesh tools (`AnalyseMesh`, `AutoSmoothMeshLines`, `CheckMesh`,
`DetectEdges`, `RecursiveSmoothMesh`, `SmoothMesh`, `SmoothMeshLines`,
`SmoothMeshLines2`); material models/conversion (`CalcDebyeMaterial`,
`CalcDjordjevicSarkarApprox`, `CalcDrudeMaterial`, `CalcLorentzMaterial`,
`Convert_VF_DiscMaterial`, `CreateDiscMaterial`); import/visualization
(`CSXGeomPlot`, `ImportPLY`, `ImportSTL`, `searchBinary`); serialization
(`WriteCSX`, `struct_2_xml`); and exporters (`export_empire`,
`export_excellon`, `export_gerber`, `export_povray`). `DirChar2Int` and
`isOctave` are also public helpers. The scan found 114 function declarations
across the 70 public/private M-files; local functions are included in that
count and are not separate public entry points.

The documented test entry point is `python -m unittest` from
`CSXCAD/python/tests`. `test_XML_RoundTrip.py` covers non-default property
attributes and material/excitation-related values, among other XML round-trip
cases. The visible suite also covers wrapper identity/ownership and stale
handle invalidation (`test_WrapperCache.py`), primitive geometry and containment
(`test_CSPrimitives.py`), transforms and multiplication order
(`test_CSTransform.py`), grid sorting/snapping/simulation area
(`test_CSRectGrid.py`), mesh smoothing and symmetry (`test_SmoothMeshLines.py`),
structure/property management (`test_CSXCAD.py`, `test_CSProperties.py`), and
direction parsing (`test_Utilities.py`). These test modules later ran in the
WSL baseline, which passed 150 tests with one skipped. The initial audit
environment lacked the installed extension; specific malformed-input and
method-level edge cases listed below remain uncovered.

### Direction utilities and mesh smoothing

| Helper | Source-level contract |
| --- | --- |
| `CheckNyDir(ny)` | Maps integer values 0/1/2, Cartesian `x/y/z`, and cylindrical `r/a/z` to 0/1/2; invalid inputs raise `ValueError`. It does not consult the active coordinate system. |
| `GetMultiDirs(dirs)` | Asserts `type(dirs) is str`, sorts the characters, and maps supported one-, two-, three-axis, or `all` combinations to integer lists. Unsupported strings have no explicit error branch and return `None`. |
| `RegisterWrapperFactory(kind, factory)` / `WrapperFromAddress(addr, kind)` | Registry keys are `int(kind)`; lookup returns `None` when no factory has been registered, otherwise calls the factory with the address. |
| `CheckSymmetry(lines)` | Uses a relative tolerance of `1e-10` over the line range and returns 0 for asymmetric, 1 for symmetric odd-count, or 2 for symmetric even-count input. |
| `SmoothMeshLines(lines, max_res, ratio=1.5, check_symmetry=True, **kw)` | Deduplicates/sorts first, optionally detects and mirrors symmetric input, splits gaps above `max_res * (1 + 1e-10)`, and snaps mirrored results back to original fixed lines. `ratio` is asserted greater than 1 only when `SmoothRange` is reached; extra `kw` is accepted but unused. |

The pure-Python smoothing helper's visible tests cover no-op input, maximum
spacing, endpoints, symmetry, exact preservation of a user line, disabling
symmetry detection, sorted output, uniform two-point meshes, and grid
direction isolation. `test_Utilities.py` covers direction aliases, invalid
directions, all supported direction combinations, order independence, and
non-string assertions. These modules ran in the later WSL suite; cases not
listed in their visible assertions remain unverified. `MeshLinesSymmetric`,
`Unique`, `SmoothRange`, and `SnapToLines` are implementation helpers rather
than intended public API.

### CSProperties base and material contracts

`CSProperties.pyx`'s base wrapper provides property type dispatch, common
metadata/attributes, primitive creation, and copy operations. The current
source-level contracts are:

| Surface | Source-level contract |
| --- | --- |
| `fromType` / `fromTypeName` | Dispatches the listed native type IDs/names to concrete wrappers; `fromTypeName` accepts both `Discrete-Material` and `DiscMaterial`. Unknown values return `None`. `no_init=True` with any keyword options raises generic `Exception`. |
| Common property constructor | The base class is not directly instantiable. Concrete constructors consume `name`, `color`, and `alpha` (default 255); leftover keywords raise generic `Exception`. |
| `GetCopy(incl_prim=False)` / `copy` | Returns a new wrapper around native copy; primitives are excluded by default and included when true. |
| Primitive access | `GetQtyPrimitives` forwards the count; `GetPrimitive` wraps negative indices modulo the count and returns `None` for a native null result; `GetAllPrimitives` returns a Python list of indexed results. The negative-index path has no empty-count guard. |
| Type and identity | `GetType`, `GetID`, and `GetMaterial` forward native values; `GetTypeString` and `GetName` decode UTF-8; `SetName` UTF-8 encodes the input. |
| Colors | `SetColor` calls `SetFillColor` and `SetEdgeColor`; both setters parse with `hex2color` and pass alpha (default 255) without wrapper range validation. `GetFillColor` and `GetEdgeColor` return `(R, G, B, alpha)` tuples. |
| Visibility / coordinate input | `GetVisibility` / `SetVisibility` forward directly. `SetCoordInputType` casts the argument to the native coordinate enum without range checking; `GetCoordInputType` returns its native value. |
| Attributes | `ExistAttribute`, `GetAttributeValue`, `SetAttributeValue`, `RemoveAttribute`, `GetAttributeNames`, and `GetAttributes` UTF-8 encode/decode names and values; names are returned as a tuple and `GetAttributes` rebuilds a dictionary. `AddAttribute` aliases `SetAttributeValue`. Missing value lookup returns the native empty string in the visible test. |
| Primitive conveniences | `AddPoint`, `AddBox`, `AddCylinder`, `AddCylindricalShell`, `AddSphere`, `AddSphericalShell`, `AddPolygon`, `AddLinPoly`, `AddRotPoly`, `AddCurve`, `AddWire`, `AddPolyhedron`, `AddPolyhedronReader`, and `AddMultiBox` pass geometry arguments/options through the typed primitive factory. `AddMultiBox` accepts an optional boxes iterable; an unrecognized factory result raises generic `Exception`. |

The visible `test_CSProperties.py` covers common name/attribute operations,
attribute copying, color spellings and alpha, visibility/copy isolation,
property type strings, primitive convenience creation, negative and null
primitive lookup, and copy-with/without-primitives. Most malformed metadata
and primitive keyword paths are not exercised.

For `CSPropMaterial`, construction extracts `epsilon`, `mue`, `kappa`,
`sigma`, and `density` from keyword arguments before delegating remaining
common keywords to the base wrapper. The material-specific contract is:

| Method | Source-level contract |
| --- | --- |
| `SetIsotropy` / `GetIsotropy` | Forward the value/state to native code without Python boolean validation. |
| `SetMaterialProperty(**kw)` | `density` is sent to the scalar density setter. Other recognized names accept a scalar (`numpy.ndim(value)==0`) or assert a length-3 vector and set directions 0, 1, 2. Unknown names raise generic `Exception` through the directional dispatcher. |
| `GetMaterialProperty(name)` | `density` is scalar; isotropic material values are scalar; anisotropic values are a NumPy length-3 array. |
| `SetMaterialWeight(**kw)` | Density encodes one UTF-8 string; other properties accept a string for the isotropic path or assert a length-3 string sequence. The documented expression variables include Cartesian/cylindrical/spherical coordinates and are not scaled by drawing unit. |
| `GetMaterialWeight(name)` | Returns the density/isotropic expression as a decoded string or the anisotropic expressions as a three-element Python list. |

Visible tests cover scalar/vector properties, isotropic/anisotropic output
shape, NumPy scalar inputs, expression weights, density expressions, and copy
preservation. Unknown property names, malformed vectors, non-string weight
members, and density type/error behavior remain untested; the later WSL suite
passed with the compiled extension but did not directly exercise these error
cases.

### CSPrimitives base and geometry contracts

The primitive factory maps supported native type IDs to concrete wrappers;
`USERDEFINED` raises an explicit not-implemented `Exception`, and an unknown
type raises generic `Exception`. Wrapper construction accepts `priority` and
rejects leftover keywords. `GetCopy(prop=None)` requests a native copy, with
an optional destination property pointer; `copy` is an alias. Primitive
wrappers retain their C++ owner and raise `RuntimeError` when the underlying
object has been invalidated.

| Base method | Source-level contract |
| --- | --- |
| `GetID`, `GetProperty`, `GetParameterSet`, `GetType`, `GetTypeName` | Forward native identity/owner/type values; `GetTypeName` decodes UTF-8. |
| `SetPriority` / `GetPriority` | Forward priority without wrapper-side range checking. |
| `GetBoundBox` | Copies six native values into a NumPy `(2, 3)` array. |
| `GetDimension` / `IsInside(coord, tol=0)` | Dimension forwards directly; `IsInside` copies the first three indexed coordinates into native doubles and forwards the tolerance. |
| `GetPrimitiveUsed` / `SetPrimitiveUsed` | Forward the native used flag. |
| `GetTransform` / `AddTransform` / `HasTransform` | `GetTransform` retrieves/creates the transform wrapper; `AddTransform` delegates to it. `HasTransform` queries without creating one. |
| `SetCoordinateSystem(cs_type)` / `GetCoordinateSystem` | Setter asserts Cartesian, cylindrical, or `None`; `None` maps to native undefined. Getter maps native undefined back to `None`. |
| `Update` | Returns the native success value and the converted diagnostic string. |

| Class | Methods | Source-level contract |
| --- | --- | --- |
| `CSPrimPoint` | `SetCoord` / `GetCoord` | Setter asserts a length-3 coordinate; getter returns a NumPy length-3 array. |
| `CSPrimBox` | `SetStart` / `SetStop` / `GetStart` / `GetStop` | Setters assert length-3 coordinates; getters return NumPy length-3 arrays. |
| `CSPrimCylinder` | `SetStart` / `SetStop` / `GetStart` / `GetStop`, `SetRadius` / `GetRadius` | Axis endpoints use length-3 vectors; radius is forwarded without a wrapper-side nonnegativity check. |
| `CSPrimCylindricalShell` | `SetStart` / `SetStop` / `GetStart` / `GetStop`, `SetRadius` / `GetRadius`, `SetShellWidth` / `GetShellWidth` | Adds shell width to the cylindrical geometry; radius and width are forwarded without wrapper-side nonnegativity checks. |
| `CSPrimSphere` | `SetCenter` / `GetCenter`, `SetRadius` / `GetRadius` | Center uses a length-3 vector; radius is forwarded without a wrapper-side nonnegativity check. |
| `CSPrimSphericalShell` | `SetCenter` / `GetCenter`, `SetRadius` / `GetRadius`, `SetShellWidth` / `GetShellWidth` | Adds shell width to the spherical geometry without wrapper-side nonnegativity validation. |
| `CSPrimPolygon` | `SetCoords` / `GetCoords` / `GetQtyCoords` / `ClearCoords`, `SetNormDir` / `GetNormDir`, `SetElevation` / `GetElevation` | Coordinates are two equal-length, nonempty arrays; normal direction is normalized by `CheckNyDir`; elevation forwards directly. |
| `CSPrimLinPoly` | `SetLength` / `GetLength` | Extrusion length forwards directly to native code. |
| `CSPrimRotPoly` | `SetRotAxisDir` / `GetRotAxisDir`, `SetAngle` / `GetAngle` | Normalizes the rotation axis; angle input is a two-element radian pair and endpoints are forwarded without degree conversion. |

The visible `test_CSPrimitives.py` exercises owner/type/priority behavior,
copy independence, geometry accessors, dimensions/bounds/inside checks,
transforms, coordinate-system defaults, and the listed shape families; the
module ran in the later WSL suite. Malformed coordinates, negative
dimensions/radii, invalid coordinate enums, and native geometry-update failure
paths remain unvalidated.

### Curve, polyhedron, reader, and multibox contracts

| Primitive | Source-level contract |
| --- | --- |
| `CSPrimCurve` | Constructor `points` requires three coordinate arrays. `SetPoints(x,y,z)` asserts equal nonzero lengths, clears previous points, and appends triples; `AddPoint` asserts length 3. `GetPoint` raises generic `Exception` on native invalid-index result and returns a NumPy length-3 array. `ClearPoints` and `GetNumberOfPoints` forward directly. |
| `CSPrimWire` | Inherits curve point handling and adds direct `SetWireRadius`/`GetWireRadius` forwarding, without wrapper-side range checks. |
| `CSPrimPolyhedron` | `AddVertex` forwards three scalars. `GetVertex` uses assertions for nonnegative/in-range index and non-null native data, returning a NumPy length-3 array. `AddFace` forwards the vertex collection; `GetFace` checks range and null result with generic `Exception`, returning an `int32` NumPy array. `Reset`, `GetFaceValid`, `GetNumVertices`, and `GetNumFaces` forward to native code. |
| `CSPrimPolyhedronReader` | `SetFilename` chooses STL type 1 only for a lowercase `.stl` suffix, PLY type 2 only for lowercase `.ply`, else type 0, then UTF-8 encodes the path. `GetFilename`, `SetFileType`, and `GetFileType` directly read or forward native values. `ReadFile` raises `RuntimeError` on native failure and otherwise returns its success value. |
| `CSPrimMultiBox` | Constructor iterates `(start, stop)` pairs. `AddBox` asserts both vectors have length 3, appends coordinates, and returns `self`; `GetQtyBoxes` forwards the native count; `GetBox` returns two NumPy vectors. `DeleteBox` and `ClearOverlap` forward directly. `GetBox` only asserts `idx < count` and has no explicit negative-index guard; `DeleteBox` likewise has no wrapper-side range check. |

Visible tests cover curve point count/copy/clear, wire radius and points,
polyhedron faces/inside/copy, reader import from the repository STL fixture,
and primitive inclusion without explicit `Update`. The negative multibox
index path and invalid reader file/suffix cases are not covered. The visible
test modules passed in the later WSL suite; these edge paths remain unverified.

### Dispersive and discrete materials

`CSPropDispersiveMaterial` exposes `GetDispersionOrder` /
`SetDispersionOrder`, `GetDispersiveMaterialProperty` /
`SetDispersiveMaterialProperty`, and `GetDispersiveMaterialWeight` /
`SetDispersiveMaterialWeight`. The getter/setter calls that take an order check
`0 <= order < GetDispersionOrder()` and raise `IndexError` otherwise; setting
the order forwards directly. Property values use isotropic scalars or
anisotropic length-3 vectors, while weight expressions use a string or a
length-3 sequence. The visible Lorentz test expects resetting the order to
clear stored coefficients.

| Material | Accepted property names in the wrapper |
| --- | --- |
| `CSPropLorentzMaterial` | `eps_plasma`, `eps_pole_freq`, `eps_relax`, `mue_plasma`, `mue_pole_freq`, `mue_relax`; each has property and weighting-function accessors. |
| `CSPropDebyeMaterial` | `eps_delta`, `eps_relax`; each has property and weighting-function accessors. |

Unknown names fall through to the base dispatcher and raise generic
`Exception`. `test_CSProperties.py` covers Lorentz/Debye order bounds,
coefficient set/get, weighting expressions, copies, and the order-reset
behavior. Anisotropic dispersive vectors and invalid property names remain
untested.

`CSPropDiscMaterial` optionally consumes `filename`, `filetype`, `scale`, and
`use_db_background`; a filename without explicit `filetype` selects type 0
(HDF5). `SetFilename` UTF-8 encodes without an explicit string type check and
`GetFilename` decodes; `SetFileType` / `GetFileType`, `SetScale` / `GetScale`,
and `SetUseDataBaseForBackground` / `GetUseDataBaseForBackground` forward
values directly. `ReadFile` returns the native boolean.
`GetEpsilonWeighted`, `GetMueWeighted`, `GetKappaWeighted`, and
`GetSigmaWeighted` take a Cython `int` component plus the first three indexed
coordinates; `GetDensityWeighted` uses only coordinates. The HDF5 test fixture
records version 2.0,
`/mesh/x`, `/mesh/y`, `/mesh/z`, a `/DiscData` cell-index dataset shaped
`(nz-1, ny-1, nx-1)`, `DB_Size`, and material-value arrays `epsR`, `mueR`,
`kappa`, `sigma`, and `density`. Visible tests exercise every material field
at all test cells, out-of-mesh fallback, and database-index-zero background
semantics.

Discrete-material `GetTransform` lazily returns a wrapper; `SetTransform`
transfers ownership to the property, refreshes the wrapper owner, and accepts
`None` to remove the transform. The test suite covers identity, replacement,
same-object assignment, removal, and transform-preserving copies; these
runtime tests, including HDF5 file reads, ran in the later WSL suite. Invalid
shapes, string subclasses, path edge cases, and invalid component indices
remain unverified.

### Probe and dump property contracts

`CSPropProbeBox` consumes constructor keywords `p_type`, `weight`,
`over_sampling`, `norm_dir`, `frequency`, and `mode_function`; unknown options
are passed to the common property constructor. Probe type, weighting,
oversampling, and normal direction otherwise forward directly through
`SetProbeType` / `GetProbeType`, `SetWeighting` / `GetWeighting`,
`SetOverSampling` / `GetOverSampling`, and `SetNormalDir` / `GetNormalDir`,
without Python enum/range checks. The probe contract table is:

| Method | Source-level contract |
| --- | --- |
| `AddFrequency(freq)` | Uses `numpy.isscalar` to add one sample; otherwise iterates the supplied object and adds each value. |
| `SetFrequency(freq)` / `ClearFrequency` | `SetFrequency` clears all existing samples before calling `AddFrequency`; invalid iterables can therefore fail after the previous values have been cleared or some replacements added. |
| `GetFrequency` / `GetFrequencyCount` | Returns a NumPy array copied from the native vector and a native sample count, respectively. |
| `SetModeFunction(mode_fun)` / `GetModeFunction` | Asserts length 3, coerces every entry with `str(...)`, UTF-8 encodes it, and returns a decoded list of three strings. |
| `SetModeFile(fileName)` / `GetModeFile` | Setter requires exact built-in `str` and UTF-8 encodes the path; getter decodes native text. |
| `SetModeOrigin(origin)` / `GetModeOrigin` | Setter asserts three coordinates and forwards them; getter returns a three-element Python list. The documented origin is Cartesian. |

`CSPropDumpBox` inherits probe behavior and consumes `dump_type`,
`dump_mode`, `file_type`, `opt_resolution`, and `sub_sampling`.
`SetDumpType` / `GetDumpType`, `SetDumpMode` / `GetDumpMode`, and
`SetFileType` / `GetFileType` pass values through without Python-side enum
validation. `SetOptResolution` / `GetOptResolution` and
`SetSubSampling` / `GetSubSampling` assert three input elements and return
NumPy length-3 arrays from their getters. Source
documentation identifies dump type families for E/H/current/D/B, SAR and raw
SAR data, interpolation modes, VTK/HDF5 file types, and warns about Yee-grid
interpolation artifacts.

Visible tests cover probe frequencies and copy isolation, probe types,
weighting, normal direction, mode function/file/origin and constructor
keywords, dump type/mode/file type/resolution/subsampling, and XML round trips.
Malformed frequencies, mode-function coercion edge cases, invalid enum values,
and malformed resolution/subsampling are not covered. The test module passed
in the later WSL suite; those specific error paths remain source-only.

### Excitation property contracts

`CSPropExcitation` constructors consume `exc_type`, `exc_val`, `delay`, and
`weight_file`, then send remaining options through the common property
constructor. The wrapper's vector/string/file-facing methods have these
contracts:

| Method | Source-level contract |
| --- | --- |
| `SetExcitType` / `GetExcitType`, `SetEnabled` / `GetEnabled` | Direct native forwarding; the wrapper does not check excitation enum or boolean ranges. |
| `SetExcitation` / `GetExcitation` | Setter asserts a length-3 vector and forwards each component; getter returns a NumPy length-3 array. |
| `SetPropagationDir` / `GetPropagationDir` | Setter asserts length 3; getter returns a NumPy length-3 array. |
| `SetWeightFunction` / `GetWeightFunction` | Requires exactly three entries and exact built-in `str` values (subclasses fail `type(value) is str`); UTF-8 encodes inputs and returns a decoded three-element list. |
| `SetWeightFile` / `GetWeightFile` | Setter requires exact built-in `str` and UTF-8 encodes the path. The documented HDF5 file has `/x`, `/y`, `/Vx`, `/Vy`; field arrays are `nx` by `ny`. Getter returns decoded path. |
| `SetWeightOrigin` / `GetWeightOrigin` | Setter asserts length 3 and forwards a Cartesian origin; getter returns a three-element Python list. |
| `GetWeightedExcitation(ny, coords)` | `ny` is Cython-typed `int`; the wrapper copies the first three indexed coordinates into a native double array and forwards the query. |
| `SetFrequency` / `GetFrequency`, `SetDelay` / `GetDelay` | Direct native forwarding without wrapper-side range checks. Frequency is documented for phase-velocity compensation; delay is in seconds. |

Visible tests cover basic excitation vectors/type/delay, weighting expressions,
copy, cylindrical coordinate conversion, and (when optional HDF5/SciPy
dependencies are present) file interpolation, propagation-direction
components, cylindrical-to-Cartesian queries, and copied in-memory mode data
after the source file is deleted. These tests ran in the later WSL suite;
invalid shapes, string subclasses, path edge cases, and invalid component
indices remain unverified.

### Absorbing boundary, lumped-element, and conductor properties

| Class / method | Source-level contract |
| --- | --- |
| `CSPropAbsorbingBC` constructor and accessors | Constructor recognizes `NormalSignPositive`, `PhaseVelocity`, and `AbsorbingBoundaryType`; `SetNormalSignPositive` / `GetNormalSignPositive`, `SetPhaseVelocity` / `GetPhaseVelocity`, and `SetAbsorbingBoundaryType` / `GetAbsorbingBoundaryType` forward directly without wrapper enum/range validation. Visible tests exercise Mur first-order and superabsorption values, copy behavior, constructor keywords, and XML round-trip of non-default settings. |
| `CSPropLumpedElement` constructor | Recognizes `R`, `L`, `C`, `ny`, `caps`, and `LEtype`; direction passes through `CheckNyDir`. If `LEtype` is omitted, the wrapper explicitly sets parallel topology. Other options use the base constructor. |
| Lumped-element accessors | `SetResistance` / `GetResistance`, `SetCapacity` / `GetCapacity`, `SetInductance` / `GetInductance`, `SetDirection` / `GetDirection`, `SetCaps` / `GetCaps`, and `SetLEtype` / `GetLEtype` forward directly except direction uses `CheckNyDir` and `GetCaps` converts native integer `1` to Python `True`; no wrapper-side physical-range or topology-enum validation is present. |
| `CSPropMetal` | Creates the native metal and accepts only base metadata/options. |
| `CSPropConductingSheet` | Inherits metal behavior, consumes `conductivity` and `thickness`, and exposes `SetConductivity` / `GetConductivity` and `SetThickness` / `GetThickness`; all forward directly without Python-side range validation. |

Visible tests cover lumped resistance/capacitance/direction/caps, conducting
sheet conductivity/thickness, absorbing-boundary values and copies, and
non-default XML round trips; these ran in the later WSL suite. Inductance/
topology accessors and invalid physical or enum values are not fully covered
by the unit test cases.

### CSRectGrid method contracts

The grid wrapper's callable inventory is now cross-checked against
`CSRectGrid.pyx`, `Utilities.pyx`, and the visible grid/smoothing tests:

| Method | Source-level contract |
| --- | --- |
| Constructor | Owns a new native grid unless created through the internal `no_init` wrapper path; coordinate type defaults to Cartesian and accepts `CoordSystem` or `cs_type`. Unknown keyword arguments assert. |
| `SetMeshType` / `GetMeshType` | Setter asserts that the coordinate type is Cartesian or cylindrical; getter returns the native value. |
| `SetLines` | `ny` accepts 0/1/2 or Cartesian (`x/y/z`) and cylindrical (`r/a/z`) direction names via `CheckNyDir`; asserts a nonempty collection, clears that axis, then inserts each line natively. |
| `AddLine` | Uses `numpy.isscalar` to select scalar insertion; otherwise asserts a nonempty sequence and inserts each value. Native grid behavior keeps lines sorted and unique, as asserted by the visible tests. |
| `GetQtyLines` / `GetLine` | Direction is normalized by `CheckNyDir`. `GetLine` uses `operator.index`, so integer-like objects such as NumPy integers are accepted; negative indices count from the end and out-of-range indices raise `IndexError`. |
| `GetLines` | Returns a NumPy array in native order. The optional `do_sort=True` parameter is deprecated and ignored; lines are maintained sorted and unique. |
| `ClearLines` / `Clear` | `ClearLines` clears one normalized direction. `Clear` clears all lines and the drawing/delta unit. |
| `SmoothMeshLines` | Defaults to `ratio=1.5` and `check_symmetry=True`; smooths one direction or all three when passed `'all'`, then replaces that direction's lines with the helper result. |
| `SetDeltaUnit` / `GetDeltaUnit` | Forward the drawing unit to/from the native grid; default unit is documented as 1 meter. |
| `Sort` | Deprecated because lines are kept sorted and unique. Accepts one direction or `'all'`; visible tests assert no change to already-normalized lines. |
| `Snap2LineNumber` | Returns `(native_index, inside_bool)` after direction normalization. Visible tests cover exact/near lines, outside endpoints, and insertion-order-independent snapping. |
| `GetSimArea` | Returns a NumPy `(2, 3)` array from the native bounding extents. Visible tests cover unsorted input line order. |
| `IsValid` | Forwards native validity; the wrapper documentation defines a valid grid as having at least two lines in every direction. |

`test_CSRectGrid.py` visibly covers coordinate type, insertion/replacement,
sorted uniqueness, deprecated sorting arguments, Python negative/bounds/index
conversion, snapping, simulation bounds, clear operations, and validity.
`test_SmoothMeshLines.py` covers spacing, endpoints, symmetry, sorted output,
and direction isolation; both modules ran in the later WSL suite. Invalid
direction values raise `ValueError` in `CheckNyDir`; the grid methods' own
`assert` validations are Python assertions, not native error codes.

### CSTransform method contracts

`CSTransform.pyx` exposes transform composition directly around native
matrices. The wrapper sets the native angle convention to radians at
construction; the higher-level rotation methods default to degree input and
convert with NumPy before forwarding. Its method-level input/output map is:

| Method | Source-level contract |
| --- | --- |
| Constructor / `copy` | An optional `ParameterSet` supplies the native backing set. `copy()` creates a distinct native transform with the same current transform state. |
| `Reset` / `HasTransform` | Forward reset and state query to native methods. |
| `Transform(coord, invers=False)` | Reads the first three indexed values into a native double vector and returns a NumPy `(3,)` array; `invers` selects native inverse transformation. There is no explicit shape check. |
| `GetMatrix` | Copies the native row-major matrix into a NumPy `(4, 4)` array. |
| `AddTransform(transform, *args, **kw)` | Asserts an exact built-in `str` name; dispatches `RotateAxis`, `RotateOrigin`, `Translate`, `Scale`, `Matrix`, or `SetMatrix`; an unknown name raises generic `Exception`. |
| `Translate(vec, concatenate=True)` | Asserts length 3, converts indexed elements to native doubles, and forwards the concatenate flag. |
| `SetMatrix(mat, concatenate=True)` | Converts input with `numpy.array`, asserts shape `(4, 4)`, flattens row-major to native doubles, and forwards; invertibility is described but not checked in this wrapper. |
| `RotateOrigin(vec, angle, deg=True, concatenate=True)` | Asserts a length-3 axis; converts degrees to radians by default, with `deg=False` preserving radians. |
| `RotateAxis(ny, angle, deg=True, concatenate=True)` | Normalizes axis using `CheckNyDir` (0/1/2 or `x/y/z`/`r/a/z`), converts degrees by default, and forwards the native axis rotation. |
| `Scale(scale, concatenate=True)` | Built-in `float` or `int` uses the scalar native overload; otherwise asserts length 3 and converts a vector. NumPy scalar classes do not take the exact built-in-type branch. |
| `SetPreMultiply` / `SetPostMultiply` | Select multiplication order for subsequent transforms; post-multiplication is the default. |

The visible `test_CSTransform.py` exercises identity/reset/state, translation,
axis and arbitrary-axis rotation, scalar/vector scaling, matrix round-trip,
inverse transforms, multiplication order, and independent copies; the module
ran in the later WSL suite. Malformed transform names, shape/type assertion
paths, singular matrices, zero axes, and NumPy scalar inputs are not covered
by these tests and remain compatibility cases.

### Wrapper lifetime and cache regression contracts

`ParameterSet` has no public Python methods beyond construction/wrapping; it
exposes the native parameter-set pointer to other wrappers. Its address lookup
uses a weak-value cache, registers a C++ destruction callback that nulls the
wrapper pointer, and records the native owner. `ContinuousStructure`
similarly registers a callback and, in `__dealloc__`, deletes a structure
created by the Python wrapper only when it is not already owned by another
native object. Borrowed (`no_init`) wrappers do not delete the underlying C++
instance. Invalidated property, primitive, or transform wrappers raise
`RuntimeError` when dereferenced; their stale cache entry is not returned by
`fromPtr`.

`test_WrapperCache.py` covers address reuse across property/primitive types,
stale-handle errors, structure-owned grid/background/parameter-set identity,
live-wrapper identity, owner-reference changes after property removal/deletion
and transform transfer, and exact cache eviction under object churn. The test
comment in `test_structure_owned_parts_survive_a_property_purge` says there is
no `ContinuousStructure.__dealloc__` and the native structure leaks; that
comment conflicts with the current `CSXCAD.pyx` implementation, which defines
`__dealloc__` and conditionally deletes its native pointer. This test comment
is stale: the implementation has `__dealloc__`, and the
targeted seven-test wrapper-cache suite passed in WSL. Additional destructive
ownership-transfer and solver/native ownership paths still need direct
coverage.

## Matlab/Octave surface and XML path

The M-file API is pure Matlab/Octave and constructs a struct consumed by
`WriteCSX`. The public workflow starts with `InitCSX`, uses `Add*` and
`Define*` helpers for properties, primitives, mesh, background, and
coordinate-system data, then writes through `struct_2_xml`. The `ATTRIBUTE`
field becomes XML attributes, struct fields become child elements, and cells
preserve repeated child elements. The MATLAB writer uses Java XML utilities;
the Octave path uses `octave_struct2xml_2` and formats numeric values to 15
digits. `InitCSX` documents spherical coordinate input as not implemented.

`WriteCSX` and the C++ serializer both target the public `ContinuousStructure`
XML format, but byte-for-byte output and all property/primitive combinations
have not been compared. The Octave writer's escaping and numeric edge behavior
also remain untested.

On MATLAB R2025b, the documented `InitCSX` → `AddMetal` → `AddBox` →
`WriteCSX` workflow succeeded. It emitted a `ContinuousStructure` root with
`CoordSystem="0"`, a `Metal` property, and the requested `Box` priority and
`P1`/`P2` coordinates. The temporary XML file was removed after inspection.
Octave was not available during the initial audit; the later WSL baseline
passed the openEMS Octave suite, but no separate CSXCAD M-file suite was found
in the inspected interface/test inventory.

### MATLAB/Octave entry-point and XML contracts

| Entry point | Source-level contract |
| --- | --- |
| `InitCSX(varargin)` | Initializes `Properties=[]` and `ATTRIBUTE.CoordSystem=0`; consumes name/value pairs into root attributes without validating keys or coordinate-system values. Odd argument counts fail by indexing the missing value. |
| `DefineRectGrid(CSX, deltaUnit, mesh)` | Stores `DeltaUnit` and the root coordinate system. Uses `mesh.x`/`mesh.y`, or cylindrical `mesh.r`/`mesh.a` only when `CoordSystem==1`; missing required X/R or Y/A produces an explicit error. `mesh.z` is accessed directly and therefore fails through MATLAB's normal missing-field error. |
| `WriteCSX(filename, CSX)` | Calls `struct_2_xml(filename, CSX, 'ContinuousStructure')`; it has no separate validation or return contract. |
| `struct_2_xml(filename, xml_struct, rootName)` | MATLAB uses Java DOM plus `xmlwrite`; Octave opens the target with `fopen`, writes the XML declaration and recursively serialized content, then closes the file. The Octave path does not check the `fopen` result. |
| `vector2str(vec, acc=9)` | Serializes elements individually with `num2str` (or a `sprintf` workaround for old Octave), joins them by commas, and formats the explicit XML-writer calls at precision 15. Empty vectors return `''`; multidimensional inputs are traversed linearly. |

MATLAB's `private/struct_2_xmlNode` serializer treats `ATTRIBUTE` specially,
converts numeric and logical attributes with 15-digit `vector2str`, and uses
DOM text nodes for character values (so the XML library handles escaping).
Struct fields become child elements, cells become repeated same-named
children, empty values are omitted, and numeric values become comma-separated
text. Unhandled MATLAB field types have no serialization branch.

The Octave serializer recursively emits text without an XML-escaping helper.
Unlike the MATLAB serializer, it emits empty values as empty elements; its
attributes and text are concatenated into XML directly. Numeric and logical
attributes use `vector2str`, and cell contents preserve repeated children.
These source differences mean empty strings/arrays and special XML characters
are not equivalent across runtimes. WSL Octave probes confirmed raw `A&B`
attribute/text output, an explicit `<Empty></Empty>` element for an empty
numeric field, and an invalid-path failure at `fprintf` with stream `-1`
after the unchecked `fopen`.

Besides the representative workflow above, a MATLAB R2025b probe confirmed
that the DOM writer escapes `&` in both attribute and text values and omits an
empty numeric field. Unmatched `InitCSX` name/value arguments and unsupported
struct field types remain unverified.

### M-file property and primitive construction contracts

| Entry point/helper | Source-level contract |
| --- | --- |
| `AddProperty(CSX, type, name, varargin)` | Rejects a property name already found in any property type; creates/extends a cell array keyed by `type`, sets `ATTRIBUTE.Name`, and consumes remaining name/value pairs as attributes. It checks that each key is a character vector but does not explicitly validate even argument count. |
| `Add2Property(CSX, propName, newPrim, primName)` | Resolves the property's type and position, errors when either lookup fails, and appends the primitive into a same-named cell list under `Primitives`. |
| `AddPrimitiveArgs(primitive, varargin)` | Extracts the first exact-case `Transform` pair into nested transformation attributes; remaining pairs become primitive attributes. It expects pair-shaped arguments and a pair-shaped transform cell without an explicit format validator. |
| `AddBox(CSX, propName, prio, start, stop, varargin)` | Builds `Priority`, `P1`, and `P2`; reads exactly the first three indexed values from each endpoint, applies `AddPrimitiveArgs`, then appends a `Box`. Coordinate shape and priority are not validated by this wrapper. |
| `AddMaterial(CSX, name, varargin)` / `AddExcitation(CSX, name, type, excite, varargin)` | Route to `AddProperty`; material options become attributes, while excitation first adds `Type` and `Excite`. They inherit the helper's duplicate-name and pair-parsing behavior. `AddPlaneWaveExcite` wraps `AddExcitation` with type 10, `E_dir`, propagation direction, and frequency compensation defaulting to 0 when omitted. |
| `AddProbe(CSX, name, type, varargin)` | Requires `name` to be `char`; option keys are case-insensitive. `Frequency` becomes `FD_Samples`; `ModeFunction`, `ModeFile`, and `ModeOrigin` use dedicated XML fields; weight, normal direction, start/stop time, and oversampling flow through property attributes. Unknown keys warn, and mode function/origin lengths are indexed without explicit shape checks. |
| `AddDump(CSX, name, varargin)` | Creates `DumpBox`, defaults `DumpMode` to 1, and stores exact-case `Frequency` as `FD_Samples`; other key/value options become attributes after checking that keys are character vectors. Option matching is case-sensitive and odd argument counts are not explicitly validated. |

The helpers have no dedicated M-file unit suite in the inspected inventory.
The documented MATLAB XML example exercised `AddMetal` and `AddBox`, but did
not cover malformed helper arguments, duplicate names, `AddProbe` or `AddDump`
option handling, or transformations. These contracts remain source-mapped
until the corresponding cases can be exercised against MATLAB/Octave and the
native XML reader.

One focused MATLAB R2025b probe passed an unknown `AddProbe` option with value
`42`; the warning reported `"*"` as the unknown key instead of the supplied
option name, because the warning formats the value position. This confirms the
source-observed warning mismatch, but does not establish the intended
replacement behavior.

### Material/property helpers

| Entry point | Source-level contract |
| --- | --- |
| `AddMetal(CSX, name)` | Reuses an existing property only when the same name is already a `Metal`; otherwise calls `AddProperty`, which rejects cross-type name collisions. |
| `AddConductingSheet(CSX, name, conductivity, thickness)` | Zero conductivity or thickness falls back to `AddMetal`; negative values error. It warns below `1e6` conductivity, below `1e-6` thickness, and above `500e-6` thickness, then stores conductivity/thickness attributes. |
| `AddLumpedElement(CSX, name, direction, varargin)` | Converts direction through `DirChar2Int` and stores it with the remaining options as a `LumpedElement` property. |
| `AddDebyeMaterial` / `AddLorentzMaterial` | Create `DebyeMaterial` and `LorentzMaterial` properties through the shared `AddProperty` path; material constants are set separately through `SetMaterialProperty`. |
| `SetMaterialProperty(CSX, name, varargin)` / `SetMaterialWeight(...)` | Resolve the property's type by name and write name/value pairs under its `Property` or `Weight` child attributes. They rely on `SetPropertyArgs` and do not apply material-value or expression validation here. |
| `AddDiscMaterial(CSX, name, varargin)` | Separates exact-case `File`, `Scale`, and `UseDBBackground` into `DiscFile.ATTRIBUTE` with `Type=0`, and `Transform` into transformation child attributes; remaining pairs go through `AddProperty`. It does not validate the file or option value types in this wrapper. |
| `AddDjordjevicSarkarMaterial(CSX, matName, varargin)` | Uses `inputParser` validators for a struct/name and required measurement parameters, requires `f1` for low-frequency mode 0 or `epsRdc` for mode 1, computes a Debye approximation, then adds a Debye material and writes permittivity, conductivity, and indexed relaxation terms. |

These helpers are source-mapped; the MATLAB example tested the `AddMetal`
creation path, but not conducting-sheet thresholds, lumped options, dispersive
material values, discrete-material HDF5 loading, or the Djordjevic-Sarkar fit.
No dedicated CSXCAD M-file test suite was found.

Property lookup helpers scan the `CSX.Properties` type fields in field-name
order and compare `ATTRIBUTE.Name` with case-sensitive `strcmp`. `FindProperty`
returns an empty type and position 0 when no name is found; `GetPropertyType`
requires `CSX.Properties` and returns an empty string for an empty property
collection. `GetPropertyPosition` validates `name`/`type` as character vectors,
errors when `type` is empty or `Properties` is absent, and returns 0 when a
nonempty type field is not present. `AddPropAttribute` uses the resolved type
and position to set `Attributes.ATTRIBUTE.<att_name>`; it does not explicitly
check for an empty type before dynamic field access.

`CheckSymmtricLines` compares mirrored lines around the midpoint of the first
and last entries with tolerance `range * 1e-10 / numel(lines)`; its source
assumes the caller has already sorted and deduplicated the input.

### M-file primitive constructors

The geometry helpers below build nested struct fields and append them through
`Add2Property`; they do not independently check coordinate counts, geometric
validity, or property/primitive compatibility.

| Constructor family | Source-level contract |
| --- | --- |
| `AddBox`, `AddCylinder`, `AddCylindricalShell` | Store priority and endpoint coordinates in `P1`/`P2`; cylinder variants add radius and the shell width. |
| `AddSphere`, `AddSphericalShell` | Store priority, center coordinates, and radius; the shell variant adds `ShellWidth`. |
| `AddPoint` | Stores priority and X/Y/Z directly as primitive attributes. |
| `AddCurve`, `AddWire` | Emit repeated `Vertex` children from a 3-by-N points matrix; `AddWire` also stores `WireRadius`. |
| `AddPolygon`, `AddLinPoly` | Convert the normal direction with `DirChar2Int`, store elevation and 2D repeated vertices; `AddLinPoly` adds extrusion `Length`. |
| `AddRotPoly` | Stores normal and rotational-axis directions, start/stop angle (default `[0, 2*pi]` when omitted), and 2D vertices. |
| `AddPolyhedron` | Serializes each supplied vertex and face with `vector2str`; the helper does not reindex or validate the closed-surface/winding requirements described in its documentation. |
| `ImportSTL` / `ImportPLY` | Create `PolyhedronReader` primitives with priority, filename, and a fixed `FileType` value (`STL` or `PLY`), then forward optional transforms. File parsing is deferred to the native reader. |

Every listed constructor passes optional arguments through
`AddPrimitiveArgs`; transformations therefore share that helper's exact-case
`Transform` parsing. This is a source map only; apart from the documented box
example, the constructors were not exercised in the current MATLAB probes.

### M-file mesh and excitation helpers

| Entry point | Source-level contract |
| --- | --- |
| `SmoothMeshLines` / `SmoothMeshLines2` | Sort and deduplicate fixed lines, fill gaps using `SmoothRange`, and optionally check spacing/ratio constraints; the first exposes a recursive repeat option, while the second iteratively recomputes adjacent gap tapers. |
| `RecursiveSmoothMesh` | Sorts/deduplicates fixed points, clamps ratios below 1.2 with a warning, tries ten initial spacings recursively with backtracking, and mirrors a detected symmetric mesh. It can return an empty result if no mesh succeeds. |
| `AutoSmoothMeshLines` | Tries selected algorithms among the three smoothers, scores output against max spacing, max ratio, symmetry, homogeneity, and minimum resolution, then returns the best-scoring result and quality. The `force_min_res` option currently sets the homogeneity flag rather than the minimum-resolution setting; an invalid algorithm selection can leave no quality result for the later selection. |
| `SmoothMesh` | Applies `AutoSmoothMeshLines` to X/R, Y/A, and Z, with scalar max-resolution/ratio values expanded across axes. A missing required mesh axis errors; non-scalar inputs are used by index without a three-entry validation. |
| `CheckMesh(lines, min_res, max_res, ratio, be_quiet)` | Checks max/min spacing and adjacent spacing ratios, returning error count, positions, and type codes when reporting is enabled. In source, all result accumulation is inside `if (~be_quiet)`, so quiet mode suppresses the returned errors as well as warnings. |
| `SetBackgroundMaterial(CSX, varargin)` | Writes each pair directly to background attributes without validating key types, even argument count, or material values. |
| `SetExcitationWeight` / `SetExcitationWeightFile` | Search the named excitation, error if the structure or excitation collection/name is missing, and set weight expressions or file/propagation-direction attributes; optional origins are serialized from the first three values without shape validation. |

MATLAB R2025b confirmed that `CheckMesh([0 2],0,1,1.3,1)` returns zero errors
and empty positions/types, while the same check with `be_quiet=0` returns one
max-resolution error at position 1 and type 1. Thus the quiet flag changes the
result contract, not just warning output. The option-routing observation for
`force_min_res` remains source-only; intent should be confirmed before changing
it.

`SmoothMeshLines` calls the shared `private/SmoothRange.m`, which constructs
start/stop geometric tapers and fills the center with equally spaced lines.
`SmoothMeshLines2` contains a separate local `SmoothRange` implementation with
special handling for missing endpoint resolutions and constrained taper
spacing. Their shared name does not indicate identical algorithms; differential
mesh outputs remain untested.

### M-file analysis, material calculations, and utilities

| Entry point | Source-level contract |
| --- | --- |
| `AnalyseMesh(lines)` | Sorts and deduplicates lines, then reports line count, max/min spacing, homogeneity, symmetry, and maximum adjacent spacing ratio. It only warns for at most one line and does not return early before reducing the resulting empty spacing arrays. |
| `DetectEdges(CSX, mesh, varargin)` | Starts from an optional mesh or initializes Cartesian/cylindrical axes from `CoordSystem`; scans configured property types and handles Box, Polygon, LinPoly, and axis-aligned Cylinder primitives. It can add translated edges, but unsupported transforms/primitives are skipped with optional warnings. |
| `CalcDebyeMaterial` / `CalcLorentzMaterial` / `CalcDrudeMaterial` | Return complex relative permittivity over the supplied frequency array; Drude delegates to Lorentz with zero pole frequencies. The formulas do not validate vector lengths or frequency domains; Debye/Lorentz conductivity terms divide by frequency. |
| `CalcDjordjevicSarkarApprox(varargin)` | Parses required measurement values and conditional low-frequency values, computes the model and a logarithmically spaced multi-term Debye fit, and returns parameter structs; `nTermsPerDec` controls `ceil(decades*nTermsPerDec)+1` poles. The integer validator for `lowFreqEvalType` does not restrict it to documented values 0/1. |
| `CreateDiscMaterial(filename, data, mat_db, mesh)` | Rejects Octave, missing `h5create`, mismatched data/mesh dimensions, and an existing output file; writes `/DiscData`, material database attributes, `/mesh/x|y|z`, and root `Version=2` to HDF5. |
| `Convert_VF_DiscMaterial(raw_filesuffix, mat_db_file, out_filename, varargin)` | Parses frequency/centering/range options, reads Virtual Family text/raw voxel inputs and a tissue HDF5 database, converts tissue Cole-Cole parameters at one frequency, then calls `CreateDiscMaterial`. If output already exists it returns early. Unknown-option handling references misspelled `varagin` and errors before warning; this was reproduced in MATLAB without reading input files. |
| `DirChar2Int(dir_char)` | Maps lowercase `x`/`r`, `y`/`a`, `z` to 0/1/2 or accepts numeric 0/1/2; other values error. |
| `isOctave()` / `searchBinary(name, searchpath, err_fail)` | Detects interpreter and parses the first three version components; binary lookup checks supplied paths then PATH, returning an empty string or throwing by default when not found. The path elements are concatenated directly with `name`. |

The Virtual Family converter also builds the final Y and Z mesh endpoints using
`dx` in the inspected source rather than `dy`/`dz`; this remains an
unexecuted source discrepancy because no fixture/database inputs are present.
No full material-fit, HDF5-generation, or edge-detection run was made.

### M-file exporters and geometry viewer

| Entry point | Source-level contract |
| --- | --- |
| `export_empire(CSX, FDTD, filename, options)` | Writes a Python script with grid lines, selected FDTD boundary/excitation settings, and supported Material/Metal Box/Cylinder/Polygon primitives; wires warn as unsupported. Its optional-options default condition is `nargin < 3` although the fourth argument is optional, and polygon export expects a nested `NormDir` vector unlike `AddPolygon`'s scalar `ATTRIBUTE.NormDir`. |
| `export_excellon(CSX, filename, options)` | Attempts to export vertical cylinders in the XY projection as Excellon drill tools, filtered by exclude/include property lists. Its nested helper calls `primitive_cylinder(fid, Cylinder)` although that helper expects `(CSX_cylinder, drawingunit)`, and it initializes `tools`/`drill` inside the property loop. |
| `export_gerber(CSX, filename, options)` | Writes RS-274X XY outlines for boxes, cylinders, and polygons from Material/Metal/ConductingSheet properties; cylindrical coordinates are polygonized in angular steps. The optional `.header` branch prints an undefined variable `header` instead of `options.header`. |
| `export_povray(CSX, filename, options)` | Writes a POV-Ray scene for boxes, cylinders, wires, and polygons; camera defaults derive from rectilinear-grid extents, with options for camera, light, header, ignored properties, and per-property modifiers. The cylinder formatter reads `P0.ATTRIBUTE.Y`, while the other coordinates and constructors use `P1`/`P2`. |
| `CSXGeomPlot(CSX_filename, args_string)` | Locates `AppCSXCAD.sh`/`AppCSXCAD.exe`, constructs a `--disableEdit` command with optional arguments, and invokes it through `system`; Windows Octave temporarily sets `QT_PLUGIN_PATH`. The system return code is not checked. |

These exporters and the viewer were source-inspected but not run. Their output
formats and unsupported primitive behavior need independent reference tests;
the source-level argument/field mismatches above should be treated as audit
leads until representative exporter fixtures are available.

### Local M-file helper inventory

| File / local function(s) | Contract or role |
| --- | --- |
| `AddDjordjevicSarkarMaterial.m`, `CalcDjordjevicSarkarApprox.m`: `isNonNegScalar`, `isPositiveScalar`, `isIntegerScalar`, `isScalar` | Return whether an input is numeric, scalar, and respectively nonnegative, positive, integer-valued, or unrestricted in sign. They are local argument validators, not public API. |
| `AutoSmoothMeshLines.m`: `eval_mesh` | Checks requested homogeneity, symmetry, and minimum resolution; returns `-1` for those failures, otherwise reduces its quality score when maximum resolution or adjacent ratio exceed their limits. Warning output is gated by `silent`. |
| `Convert_VF_DiscMaterial.m`: `GetColeData` | Matches the final path segment of a material name case-insensitively against database group names and alternate names, normalizing spaces to underscores; returns group attributes as a struct or errors when no group matches. |
| `CreateDiscMaterial.m`: `strjoin` | Joins a cell array with the supplied delimiter; it indexes the first element unconditionally, so empty input is not handled. |
| `DetectEdges.m`: `AddEdge` | Adds unique primitive coordinates to the aggregate mesh edges; it applies translation transforms and skips mismatched coordinate systems or unsupported transformations. |
| `RecursiveSmoothMesh.m`: `recursiveMeshSearch` | Recursively chooses intermediate lines within the ratio/max-spacing interval to reach the next fixed line, backtracking when the remaining fixed lines cannot be satisfied and returning a success flag. |
| `SmoothMeshLines2.m`: `calc_gaps`, `plot_lines`, `calc_start_res`, `calc_stop_res`, `SmoothRange` | Maintain merged old/new lines and boundary resolutions, calculate neighboring start/stop spacing, provide optional plotting, and generate constrained geometric tapers; the local `SmoothRange` differs from the shared helper of the same name. |
| `export_empire.m`: `gym_vect`, `gym_vector`, `primitive_box`, `primitive_cylinder`, `primitive_wire`, `primitive_polygon`, `process_primitives`, `export_empire_layer`, `export_empire_meshlines`, `convert_BC`, `export_empire_settings` | Format coordinate vectors and primitive geometry, dispatch supported primitives, emit layer and mesh blocks, map boundary-condition values, and serialize solver settings. |
| `export_excellon.m`: `coord`, `primitive_cylinder`, `process_primitives` | Format drill coordinates, convert supported cylinders to tool/drill records, and aggregate records for selected properties. |
| `export_gerber.m`: `gerber_coord`, `primitive_box`, `primitive_cylinder`, `primitive_polygon`, `GetCoordSystem`, `process_primitives` | Format coordinates and supported XY primitive outlines, determine each primitive's coordinate system, and dispatch/emit property geometry. |
| `export_povray.m`: `pov_vect`, `primitive_box`, `primitive_cylinder`, `primitive_wire`, `primitive_polygon`, `process_primitives` | Format POV-Ray vectors and primitive objects, then dispatch and emit supported geometry using the selected property modifiers. |

### Private property and XML helper contracts

| Helper | Source-level contract |
| --- | --- |
| `CheckSymmtricLines(lines)` | Assumes sorted, unique, nonempty lines; compares symmetric pairs about the midpoint of the end values using tolerance `range * 1e-10 / numel(lines)`, including the center line for odd counts. Invalid ordering, empty input, and singleton behavior are not explicitly checked. |
| `GetPropertyType(CSX, name)` | Requires a character-vector name and a `CSX.Properties` field; returns `''` for an empty property struct or when no `ATTRIBUTE.Name` matches. It scans property-type fields and their ordered cell entries and reports the first match. The missing-`Properties` error identifier is `CSXCAD:GetPropertyPosition`, not the helper's name. |
| `GetPropertyPosition(CSX, type, name)` | Requires character-vector type/name, an existing `CSX.Properties` field, and nonempty type; returns 0 if that type is absent, otherwise scans the property cell list and returns the first matching `ATTRIBUTE.Name` position or 0. |
| `FindProperty(CSX, name)` | Initializes `pos=0`, obtains the type through `GetPropertyType`, returns immediately when no type matches, and otherwise delegates the position search. A missing property therefore returns `type=''`, `pos=0`; invalid name/container inputs propagate helper errors. |
| `SetPropertyArgs(CSX, type, name, property, varargin)` | Resolves the property position and errors if it is absent; then writes name/value pairs under `CSX.Properties.(type){pos}.(property).ATTRIBUTE`. It does not validate even argument count, key type, or the nested property field before assignment; an odd trailing argument is not handled by an explicit validation branch. |
| `struct_2_xmlNode(docNode, docElem, mat_struct)` | Recursively serializes struct fields into DOM elements; numeric/logical attributes and numeric text use `vector2str(...,15)`, string cell entries become text nodes, nested structs recurse, and empty fields are omitted. DOM calls escape XML text/attribute content. Unsupported leaf types have no serialization branch and are silently skipped. The MATLAB R2025b probe confirmed ampersand escaping and omission of an empty numeric field. |
| `octave_struct2xml_2(in, rootName, indent)` | Recursively assembles XML text, serializing `ATTRIBUTE` values and numeric leaves with `vector2str(...,15)`, repeating cell children, and indenting nested structs. Unlike the MATLAB DOM path, it does not escape XML text or attributes; the WSL Octave probe confirmed raw ampersands and explicit empty elements. `struct_2_xml` passes the result as the format string to `fprintf`, so percent characters in serialized content are a source-only formatting risk. |

No direct tests were found for the property lookup/argument helpers or
symmetry helper error paths. The serializer behaviors above are covered only
by the stated focused XML probes; unsupported leaf types and percent-bearing
Octave content remain untested.

## Remaining compatibility work

- The later WSL Python suite passed 150 tests with one skipped, including the
  wrapper-cache tests. Add focused cases for malformed arguments, invalid
  native indices, and ownership paths not covered by those suites.
- Compare equivalent MATLAB/Octave and C++ output for representative XML
  structures, including repeated elements, parameters, attributes, and
  floating-point values.
- Exercise the M-file API's malformed arguments, non-default coordinate
  systems, transform, and mesh paths, and validate XML escaping and Octave
  behavior where that runtime is available.
- All public Cython method names are now present in the interface audit, and
  the 114 CSXCAD M-file declarations are inventoried, including the local
  helpers above. Some methods still lack complete defaults, conversion,
  exception, and native-side-effect contracts; those details remain in
  full-audit scope.
