# openEMS Python/Cython and Matlab/Octave Interface Audit

**Status:** Callable inventory expanded from source. The later WSL baseline
built the Python extension and solver, and passed the Python and Octave suites
listed in `../VALIDATION.md`; individual paths noted below as untested were
not directly exercised by those suites. No openEMS code was changed.

Runtime statements below describing missing Python packages, Octave, or the
solver refer to the initial Windows audit attempt unless explicitly identified
as a remaining path-specific gap; the later WSL suite results supersede those
environment-wide limitations.

## Python/Cython surface

`python/openEMS/openEMS.pyx` wraps the native `openEMS` controller and imports
the `ports`, `nf2ff`, and `automesh` helpers. The package initializer imports
CSXCAD first (for Windows DLL setup), resolves package metadata with a fallback
version, and exports the `openEMS` class. Companion Cython/native interfaces
include `_nf2ff.pyx` and `sar_calculation.pyx`; pure-Python modules include
`ports.py`, `nf2ff.py`, `automesh.py`, `utilities.py`, and `sar_utils.py`.
Generated Cython `.cpp` files are build artifacts.

The class constructor accepts timestep count, end criterion, maximum time,
oversampling, coordinate system, multigrid radii, timestep/factor/method, and
cell-constant material controls; unknown keyword arguments assert. The
documented defaults include `NrTS=1e9`, `EndCriteria=1e-5`, and
`OverSampling=4`. `SetCoordSystem` accepts Cartesian (0) and cylindrical (1);
`SetMultiGrid` rejects an empty radius list. `SetBoundaryCond` requires six
entries and accepts PEC/PMC/MUR/PML values. Its docstring says an `(8,)` array,
which conflicts with the six-entry implementation and the six FDTD faces.
`AddLumpedPort` requires geometry to have been set and can add requested grid
edges.

`SetCSX` transfers geometry ownership to the controller. C++ exposes
`SetAbort`/`CheckAbortCond`, but Python progress reporting and cancellation
semantics were not established from the inspected interface path. Python
package tests and full simulations are documented in `openEMS/AGENTS.md` and
`python/Tests/`. The initial Windows audit environment lacked the compiled
extension; the later WSL baseline built it and passed the principal Python
suite, but that suite does not directly exercise every setter or full port
post-processing path.

### Controller validation and port dispatch

The constructor applies recognized keyword options and asserts that no
unrecognized keyword remains. `SetCoordSystem` accepts values equal to 0 or
1 (so `True` compares equal to 1); `SetMultiGrid` checks only that the radii
collection is nonempty before joining its elements into a native string.
Timestep count, end criterion,
oversampling, material mode, timestep method/factor, maximum time, and
excitation values are forwarded without Python-side range checks.

`SetBoundaryCond` checks for exactly six entries despite documenting eight.
Built-in integer entries are forwarded directly without checking the enum
range; `PEC`, `PMC`, and `MUR` map to 0, 1, and 2, while strings beginning
`PML_` are parsed for a layer count using `strip('PML_')`. Unknown strings
raise a generic exception; other non-string, non-integer values may fail with
an attribute error when `.startswith` is called.
`Add*Port` methods require `CSX` to have been set and return their helper
object. Only `AddLumpedPort` handles `edges2grid`, inserting the requested
start/stop coordinates before returning the port.
`test_openEMS.py` directly checks coordinate-system selection, multigrid
nonemptiness, boundary-condition shapes/strings, excitation calls, and port
dispatch without a CSX object. Constructor tests for timestep count/end
criterion/oversampling/factor/method/cell-material options only assert that
construction succeeds; they do not inspect native values. There are no direct
tests for `Reset`, `SetCylinderCoords`, or `SetTimeStep`. The later WSL suite
passed with the compiled extension; it does not add assertions for those
setter paths.

### Callable inventory and source-observed contracts

- `openEMS.pyx` exposes controller construction/reset; timestep, coordinate,
  multigrid and material settings; excitation and boundary conditions; lumped,
  curve, waveguide, rectangular/circular waveguide, coaxial, microstrip,
  stripline and CPW ports; NF2FF box creation; CSX access; mesh-edge insertion;
  abort; XML read/write; and `Run`. Its method inventory is:
  `Reset`, `SetNumberOfTimeSteps`, `SetEndCriteria`, `SetOverSampling`,
  `SetCellConstantMaterial`, `SetCoordSystem`, `SetMultiGrid`,
  `SetCylinderCoords`, `SetTimeStepMethod`, `SetTimeStep`,
  `SetTimeStepFactor`, `SetMaxTime`, `SetGaussExcite`, `SetSinusExcite`,
  `SetDiracExcite`, `SetStepExcite`, `SetCustomExcite`, `SetBoundaryCond`,
  `AddLumpedPort`, `AddCurvePort`, `AddWaveGuidePort`,
  `AddRectWaveGuidePort`, `AddCircWaveGuidePort`, `AddCoaxialPort`,
  `AddMSLPort`, `AddStripLinePort`, `AddCPWPort`, `CreateNF2FFBox`,
  `SetCSX`, `GetCSX`, `AddEdges2Grid`, `Run`, `SetAbort`, `Write2XML`,
  and `ReadFromXML`. `__cinit__`, `__dealloc__`, `_SetLibraryArguments`,
  `_cleanup_sim_path`, and `WelcomeScreen` are also explicit class/helpers.
- `ports.py` defines `UI_data` and `Port`, plus `LumpedPort`, `MSLPort`,
  `WaveguidePort`, `RectWGPort`, `CircWGPort`, `CoaxialPort`, `StripLinePort`,
  `CPWPort`, and `CurvePort`. The declared methods are `UI_data.__init__`;
  `Port.__init__`, `_AddProbe`, `SetEnabled`, `ReadUIData`, and `CalcPort`;
  `LumpedPort.__init__` and its `CalcPort` override; `MSLPort.__init__` and
  `ReadUIData`; `WaveguidePort.__init__` and its `CalcPort` override;
  constructors for `RectWGPort`, `CircWGPort`, `CoaxialPort`, `StripLinePort`,
  and `CPWPort`, with `ReadUIData` overrides on the last three; and
  `CurvePort.__init__` and its `CalcPort` override. Shared port operations
  read and sum voltage/current probe data, separate incident/reflected waves
  using reference impedance, calculate power, and optionally shift the
  reference plane. Specialized classes supply geometry, modal fields,
  propagation constants, impedance, or probe-combination behavior.
- `nf2ff.py` defines `nf2ff` (`__init__`, `CalcNF2FF`) and `nf2ff_results`
  (`_ReadFD`). Calculation reads cached HDF5 results when enabled and
  analyzes available per-face E/H files otherwise, then checks cached radius,
  angle and frequency axes. Result loading supports both compound-complex
  data and the legacy split-real/imaginary layout.
- `automesh.py` exposes `mesh_combine`, `mesh_hint_from_primitive`,
  `mesh_hint_from_point`, `mesh_hint_from_box`, and
  `mesh_estimate_cfl_timestep`.
- `utilities.py` exposes `DFT_time2freq`, `Check_Array_Equal`, `DelayFidelity`,
  `check_mode_purity`, `get_resource_path`, and `HDF5Dump`. The reader's
  public methods are `Close`, `GetDumpTypeName`, `IsTD`, `IsFD`, `IsVector`,
  `GetNumTimesteps`, `GetNumFrequencies`, `GetTimes`, `ResetRegion`,
  `NearestIndex`, `SetPlane`, `SetLine`, `SetRange`, `SetSampling`, `GetMesh`,
  `GetFieldAtIndex`, `GetFieldAtFrequency`, `IterFD`, `IterTD`, and
  `GetAttributes`; `__enter__`, `__exit__`, and `__repr__` are also implemented.
  Its private HDF5 layout/indexing helpers are `_BuildIndex`, `_CheckDir`,
  `_CheckNoConflict`, `_DFT`, `_DecodeStr`, `_FDDataset`, `_FDName`,
  `_FixOrder`, `_Group`, `_Init`, `_MatchFrequency`, `_ProbeLayout`,
  `_ReadDataset`, `_ReadFrequencies`, `_ReadMesh`, `_ScanFDIndices`,
  `_SelectionLength`, `_SpatialSelection`, `_TDName`, and `_TimeOf`. It
  supports Cartesian, cylindrical, and spherical mesh labels and detects
  legacy versus current field layouts.
- `_nf2ff.pyx` exposes `__cinit__`, `AnalyseFile`, `SetMirror`, `SetRadius`, `Write2HDF5`,
  and `SetVerboseLevel`. `sar_calculation.pyx` defines `SAR_Calculation` with
  `SetDebugLevel`, `EnableProgress`, `SetAveragingMass`,
  `SetAveragingMethod`, `EnableAutoRange`, `EnableCubeStats`, and
  `CalcFromHDF5`; `sar_utils.py` provides `readSAR`.
- `SAR_Calculation` exposes `__cinit__`/`__dealloc__`, accepts constructor aliases `verbose`/`debug`, converts
  averaging mass from grams to kilograms, and passes averaging-method names as
  UTF-8. `CalcFromHDF5` checks only input-file existence at the Python layer
  and converts `numThreads` to an unsigned integer before entering native
  code.
- Constructor keyword processing is sequential; unknown keys raise a generic
  `Exception`. `SetAveragingMethod` returns the native boolean result, with
  `silent=True` by default. `autoRange` is converted to `float`, while
  `EnableCubeStats` is called only when the constructor option is truthy.
  `CalcFromHDF5(export_cube_stats=True)` enables cube statistics before calling
  native code; output-path validity and native failure details are not checked
  by the Python wrapper.
- `readSAR(fn, f_idx=0)` uses `HDF5Dump` as a context manager and returns
  `(GetFieldAtIndex(f_idx), GetMesh()['lines'], GetAttributes(f_idx))`.
  It reads the complete selected field, returns mesh lines in metres, and
  returns dump attributes with the SAR data. It does not independently
  validate that the file is a SAR result, that the field is scalar, or that
  the mesh is Cartesian; its documented SAR shape/coordinate guarantees
  depend on the input dump. Missing/malformed files and out-of-range indices
  propagate errors from `HDF5Dump`.

`_nf2ff.__cinit__` has scalar-handling branches for frequency/theta/phi that
call `list(float(value))`; Python floats are not iterable, so direct scalar
construction follows a `TypeError` path. Normal `nf2ff.CalcNF2FF` calls
normalize these values to lists first. Also, when the H file is missing,
`AnalyseFile` formats its error with the E filename. Both are source findings;
the specific branches were not directly exercised by the later WSL suite.

### Python NF2FF constructor and result-reader contracts

`nf2ff.__init__` defaults all six box faces on, mirror modes off, and time
domain dumps (`dump_type=0`, cell-interpolated mode 1). A scalar `frequency`
is wrapped in a list and switches both E/H dumps to frequency-domain types
10/11; it is passed to each dump's `SetFrequency`. The `directions` and
`mirror` options are asserted to have length six, ordered as the negative and
positive face for each axis. Remaining keywords pass through to both dump
constructors. Each enabled face creates one E and one H surface box.

`CalcNF2FF` wraps scalar frequency/theta/phi values, converts theta/phi from
degrees to radians for `_nf2ff`, and defaults output to
`<sim_path>/<name>.h5`. With caching enabled it reuses an existing output;
otherwise it configures six face mirrors, radius, and analyzes a face only
when both E and H HDF5 files exist. Missing pairs are skipped without a
Python-side error, after which it still writes the result. Cached/computed
result checks are conditional on `result.phi` being non-`None`: radius uses a
relative `1e-6` comparison, angle arrays use `Check_Array_Equal` tolerance
`1e-4` after converting radians back to degrees, and frequency uses relative
tolerance `1e-6`. Mismatches raise generic `Exception`.

`nf2ff_results` reads mesh axes and frequency/radiated-power/directivity
attributes eagerly, then loads E-theta, E-phi, and radiated-power arrays per
frequency. It selects legacy layout from the presence of `f0_real` under
E-theta; legacy split-complex samples and real radiated power are transposed
from `(phi, theta)` to `(theta, phi)`. The current compound-complex layout is
read directly. It derives `E_norm` as the square root of summed squared
magnitudes and circular-polarization fields from theta/phi components and
azimuth.

The synthetic HDF5 tests cover current/legacy equivalence, theta/phi/frequency
axes, derived fields, and that the file handle is released after construction;
they ran in the later WSL Python suite. They do not cover the native NF2FF
calculation, cache invalidation/mismatch, partial face-file sets, or
malformed/empty HDF5 layouts.

### Probe, numerical, and mesh-helper behavior

`ports._load_ui_file` skips blank lines, treats the last `%` comment as the
column header, and checks that a present header starts with `t/s`; it parses
data as `float64` but does not validate the expected column count before
`UI_data` indexes time/value columns. `UI_data` accepts a scalar filename or
frequency by wrapping it in a list; each probe is transformed independently.
The last column is exposed as mode purity only when the header's last name is
exactly `mode_purity`.

`DFT_time2freq` asserts equal time/value lengths and a nonempty frequency
list, computes a direct sum, scales pulse data by the first time step and
periodic data by sample count, then doubles the result for a single-sided
spectrum. It does not check for uniform time spacing. `Check_Array_Equal`
requires identical shapes and uses strict `< tol`; relative mode divides by
the reference array, so zero reference elements produce non-finite
intermediate differences. `DelayFidelity` rejects an empty frequency band and
requires a finite feed resistance; `check_mode_purity` is a no-op when purity
data is absent and otherwise checks absolute purity only where signal
magnitude exceeds the configured fraction of its peak.
No dedicated `test_*.py` assertions were found for these four utility
functions. `DFT_time2freq` and `check_mode_purity` are used by simulation
scripts, `DelayFidelity` by a tutorial, and `Check_Array_Equal` by NF2FF cache
checks; those call sites do not establish utility-level numerical regression
coverage. Their edge semantics remain source-only.

`automesh.mesh_combine` accepts a `sort` argument but always sorts when both
axis meshes are present; when only one axis list exists it returns that object
without copying it. The implementation assumes three-entry mesh containers
and list-compatible axis values. Point and box hints select axes through the
CSXCAD `GetMultiDirs` helper and optionally merge with an existing mesh.
Primitive dispatch supports only points and boxes; unsupported types return
`None`. Box hints normalize start/stop coordinates, optionally add metal-edge
refinement offsets, and support upper/lower edge switches. A transformed box
writes a warning to stderr and returns no hint (also bypassing any requested
merge). For a zero-width box axis the point coordinate is still returned even
when both edge switches are false. `mesh_estimate_cfl_timestep` squares the
minimum spacing on each of three axes, scales by `GetDeltaUnit()` and vacuum
light speed, and assumes each axis has at least two mesh lines; monotonicity,
positive spacing, and degenerate axes are not validated.
`test_Automesh.py` covers box edge hints, selected directions, flat boxes,
refinement, merging, box dispatch, unsupported sphere dispatch, and sorted
merge behavior. It does not cover point hints, transformed boxes, invalid
directions, sort=False, reference aliasing, or CFL estimation; the Python
extension dependencies prevented execution. These source behaviors need
reference tests before deciding whether to preserve or correct them.
`readSAR` returns a three-item tuple: SAR field,
mesh line arrays, and dump attributes. `test_sar_utils.py` covers missing and
non-dump files, current and legacy layouts, output shapes/values/metadata, and
out-of-range frequency indices. `test_SAR_Calculation.py` covers constructor
keywords, valid/invalid averaging methods, and a missing input file;
`test_sar_analytic.py` adds uniform-field formula, two-frequency output, and
single-/multi-thread consistency checks. These tests ran in the later WSL
Python suite; the SAR reader tests exercise scalar fixture files, not
rejection of vector or non-Cartesian dumps.

### Resource lookup across scripting interfaces

`get_resource_path(*parts)` searches at call time, in order: the `resources`
directory beside the Python package module, the source-tree `openEMS/resources`
directory, then for each nonempty `OPENEMS_INSTALL_PATH` and
`CSXCAD_INSTALL_PATH`, `<prefix>/share/openEMS/resources` and
`<prefix>/resources`. It returns the first normalized joined path for which
`os.path.exists` is true (so directories also qualify), and otherwise raises
`FileNotFoundError` listing every attempted path. The helper does not validate
the number or contents of `parts`; absolute or parent-relative segments can
escape a search root. No direct test of this helper or its precedence was found
in the Python test sources. `openEMS/CMakeLists.txt` installs the resource
directory to `share/openEMS`; `python/setup.py` copies source resources into
`python/openEMS/resources` before packaging and includes package resources in
wheel data (the sdist path expects the copied directory to already exist). The
MRI loop-coil tutorial uses the helper to locate a phantom file. These
packaging and caller paths are source-mapped only; Python package runtime
validation remains blocked.

The Matlab helper `openEMS_resource_path(varargin)` builds one resource path
relative to its own `matlab/` directory (`../resources`) and raises
`openEMS:resource_not_found` if `exist(path, 'file')` is false. This keeps
lookup independent of the caller's working directory and naturally follows
the installed `share/openEMS/matlab` and `share/openEMS/resources` layout, but
unlike Python it has no environment-prefix search or alternative-root
fallback. It forwards all `varargin` path segments without validation and
returns the joined path without an explicit normalization step. The two MRI
tutorials are the only located callers; no direct unit test was found.
MATLAB R2025b successfully resolved a bundled phantom after changing to
`tempdir`, and a missing resource raised the documented error identifier. No
direct Python helper test was found; the WSL package suite passed, but did not
exercise lookup precedence or path-segment cases.

### Physical constants

`physical_constants.py` exports `C0 = 299792458`, `MUE0 = 4e-7*pi`,
`EPS0 = 1/(MUE0*C0**2)`, and `Z0 = sqrt(MUE0/EPS0)`. MATLAB defines the same
formulas and additionally exposes lowercase `c0` as a legacy alias. The native
`tools/constants.h` stores all four as fixed `double` literals; comparison
with the Python/MATLAB formulas gives relative differences of about
`4.49e-10` for `MUE0`, `4.4e-14` for `EPS0`, and `2.05e-12` for `Z0`, consistent
with decimal rounding. Python `C0` is an integer while MATLAB and C++ expose
floating-point values. No dedicated constant tests were found; test/tutorial
scripts use the module, while `test_Ports.py` also hardcodes `C0`. These are
source and arithmetic observations, not native runtime validation.

### Probe-file and base-port contracts

`_load_ui_file(filepath)` reads all `%` comment lines and uses the final one as
the column header. A present header must begin with `t/s`; blank data lines are
skipped, and remaining whitespace-delimited values are parsed as `float64`.
Without a header it still treats columns 0 and 1 as time and signal. It does
not validate row widths, nonempty data, or that a mode-purity header has a
corresponding data column before `UI_data` indexes the arrays.

`UI_data(fns, path, freq, signal_type='pulse')` wraps a built-in string
filename and scalar frequency in lists, loads each file independently, and
calculates one DFT result per file. It only exposes mode-purity samples when
the last header token is exactly `mode_purity`. `Port.ReadUIData` sums each
voltage and current file's time/frequency data independently and records the
first file's time axis; it does not compare time axes or sample counts, and an
empty filename list fails when it indexes the first time series.

`Port.CalcPort` calls `ReadUIData` before applying an optional reference
impedance override and raises if no reference impedance is then available.
An optional reference-plane shift requires `beta`, directly accesses
`measplane_shift` and subtracts it when truthy (without a presence guard),
converts drawing units with the grid delta unit, and rotates the total
frequency-domain voltage/current before wave separation. Incident and
reflected waves are produced in frequency domain for scalar or array
impedance; time-domain waves are produced only when `type(Z_ref)` is exactly
built-in `int` or `float`. Power arrays use the real parts of voltage/current
phasor products. `SetEnabled` toggles excitation properties whose exact type
is `CSPropExcitation`; enabling with no such property raises, while disabling
with none is allowed.

The visible `test_Ports.py` exercises port constructors, geometry, probe
filenames, mode origins, excitation amplitude, and duplicate port names. It
does not directly exercise `_load_ui_file`, `UI_data`, `ReadUIData`, or
`CalcPort`; those file-layout, summation, axis-alignment, impedance, and
post-processing paths remain outside the visible suite. A synthetic WSL
probe now verifies header parsing and rejection, time-series summation,
frequency-domain wave identities, and power calculation. It does not validate
solver-produced probe files, mismatched probe time axes, mode-purity columns
through `Port`, or reference-plane shifts.

### HDF5Dump metadata, selection, and field-read contracts

| Surface | Source-level contract |
| --- | --- |
| Construction and lifetime | Accepts a path or an already-open `h5py.File`; only a file opened internally is closed by `Close`/context exit. Initialization errors close internally opened files and re-raise. The reader requires `/Mesh` and at least one `/FieldData/TD` or `/FieldData/FD` sample. |
| Mesh and layout | Mesh type IDs map to Cartesian (`x,y,z`), cylindrical (`rho,alpha,z`), or spherical (`r,theta,phi`) axes; absent or inconsistent `mesh_type` falls back to recognized axis datasets. Mesh lines and `mesh_scaling` are returned as stored. Layout uses dataset `d_order` when present, else old HDF5 version `<=0.2`, else root `legacy_fmt`; legacy spatial axes are reversed to logical `(x,y,z)` order. A vector is inferred only from a four-dimensional dataset. |
| FD inventory and metadata | Scans numeric `fN`/`fN_real` dataset names, reads group-level frequencies or per-dataset attributes, and uses `NaN` if a frequency attribute is missing. `GetAttributes` merges root, domain-group, then dataset attributes, with later values overriding earlier ones. Dump type names use a fixed table and unknown/missing values return `"unknown dump type"`. |
| File access and values | `GetFieldAtIndex` requires exactly one of `f_idx` or `t_idx`; integer indices are positional and may be negative, while strings select dataset names directly. A component may be selected by index or mesh-axis name. Compound complex datasets are read through h5py; legacy `_real`/`_imag` pairs are combined while preserving float32 as complex64. Legacy arrays are transposed to x-inner logical order. |
| Frequency access | `GetFieldAtFrequency` reads a stored FD sample within relative tolerance `1e-6`; an unmatched request in an FD-only file raises `ValueError`, while an unmatched request in a TD or mixed file is computed by DFT. The DFT requires at least two timestamps, uses only the first time interval as `dt`, accumulates every timestep with `exp(-2j*pi*f*t)`, and multiplies by `2*dt`; uniform time spacing is assumed but not checked. |
| Region selection | Directions accept `0/1/2` or the mesh's axis labels. `SetPlane` requires exactly one of position/index, uses nearest mesh line for positions, permits negative indices, and replaces a plane on another axis while retaining other ranges/sampling. `SetRange` uses half-open index limits or nearest coordinate limits with both endpoints included; plane/range conflicts on the same axis raise until reset. `SetLine` collapses the perpendicular axes and preserves a non-singleton range and sampling along the line axis. `SetSampling` accepts one or three factors and stores their integer conversions after checking each converted value is positive. |
| Mesh and iteration | `GetMesh(region=True)` returns line vectors matching the active region/sampling; `IterFD` and `IterTD` yield frequency/time with the corresponding selected field. `ResetRegion` resets all axes or one axis. `GetTimes` reads each time attribute and returns `NaN` when it is absent. |

The synthetic-fixture `test_hdf5_utils.py` covers Cartesian/cylindrical mesh
metadata and fallback detection, ownership of open file handles, scalar and
complex vector data, legacy and current layouts, dtype preservation, FD/TD
metadata and iteration, on-the-fly DFT, attributes, component selection,
region/line/plane/range interactions, and validation errors; it ran in the
later WSL 31/31 openEMS Python suite. Source-only edge cases include malformed
frequency arrays,
nonuniform or missing TD timestamps, range bounds/order, fractional sampling
factors that truncate through `int`, malformed legacy complex pairs, and
post-`Close` method calls.

### Port-specific constraints found in source

- `Port.CalcPort` requires a reference impedance (from the call or the
  subclass), computes incident/reflected voltage and current waves, then
  calculates incident/reflected/accepted power. Time-domain wave separation
  is performed only when the reference impedance is a built-in `int` or
  `float`; array-like impedances normalize the frequency-domain data.
- `LumpedPort` rejects zero length in its excitation axis, uses a resistor for
  positive `R` and a metal for `R == 0`, and has no branch for negative `R`
  before appending the local load variable. Its reference-plane warning is
  constructed with `Warning(...)` rather than emitted. These source paths
  need executable reference checks before being classified as behavior
  defects.
- `MSLPort` requires distinct propagation and excitation axes, non-identical
  start/stop coordinates, and at least six mesh lines along propagation. It
  chooses a measurement plane from the nearest mesh line (default halfway),
  optionally shifts the feed and plane, and derives propagation constant and
  reference impedance from voltage/current probe differences.
- `WaveguidePort` documents two mode sources: paired analytic E/H expressions
  or paired HDF5 mode files. The implementation validates both file paths
  only when the port is excited, so passive and mixed-source configurations
  need reference validation. Excitation types 0/1 use E and 2/3 use H;
  file-based modes also set propagation direction explicitly. `RectWGPort`
  accepts only four-character TE mode names. `CircWGPort` supports a finite
  table of TE modes and requires z propagation on a cylindrical mesh.
- `CoaxialPort` rejects zero propagation length; its termination accepts
  `Feed_R=0` (short) or infinity (open), and raises `NotImplementedError` for
  finite positive values. `StripLinePort` and `CPWPort` require the start/stop
  height coordinate to match and propagation to have nonzero length; finite
  nonnegative termination resistance is represented by a pair of symmetric
  loads, while zero adds metal. Both reject negative `Feed_R`.
- `CurvePort` snaps the requested endpoints to mesh lines and, for spans
  longer than one cell, places a one-cell port near the midpoint and connects
  the original endpoints with PEC curves. It uses a resistor for positive
  finite `R` and metal for zero; negative `R` has no explicit validation or
  load branch. Like `LumpedPort`, its reference-plane warning is constructed
  but not emitted.

`Run` resolves the simulation path before changing directory, optionally
removes whitelisted outputs, creates only the requested final directory when
absent, changes the process-wide current directory, sets native library
options, then calls native setup and run. Option names replace underscores
with hyphens; `setup-only` is aliased to `no-simulation`. Boolean true options
are emitted without a value, while false options become empty-string entries
in the native option vector. Numeric 0/1 values are treated as booleans except
for `verbose` and `numthreads`, which remain explicit integer options. The
source does not restore the previous
working directory. A nonzero setup result is printed and returned; after
successful setup, the simulation call has no explicit Python return value.
`SetAbort` forwards directly to the native controller. `ReadFromXML` clears
the Python CSX wrapper before native read/reset, while `SetCSX` transfers
native ownership. These are source observations; native execution and
cross-version behavior remain unverified.

## Matlab/Octave workflow

The primary M-file path composes `InitFDTD`, `SetBoundaryCond`,
`SetGaussExcite`, port/dump helpers such as `AddLumpedPort`, and CSXCAD
geometry, then writes the solver setup with `WriteOpenEMS` and starts it with
`RunOpenEMS`. Post-processing uses helpers such as `calcPort`,
`CalcNF2FF`, and `AnalyzeNF2FF`.

`RunOpenEMS` requires an existing simulation directory and setup filename,
appends `--legacyHDF5Dumps`, and invokes the installed solver through
`invoke_openEMS`. It supports log/silent settings and remote SSH execution
(Unix SSH or Windows PuTTY). `RunOpenEMS_Parallel` schedules jobs across a
host list and falls back to local serial execution when remote execution is
unsupported or unconfigured.

The M-file declaration scan found 96 function declarations in 76 files. The
primary interface families include setup/excitation/boundaries
(`InitFDTD`, `InitCylindricalFDTD`, `Set*Excite`, `SetBoundaryCond`), ports
(`Add*Port`, `calcPort`, `calcLumpedPort`, `calcTLPort`, `calcWGPort`),
execution/serialization (`WriteOpenEMS`, `RunOpenEMS`,
`RunOpenEMS_Parallel`, `CleanupSimPath`), NF2FF/SAR and analysis
(`CreateNF2FFBox`, `CalcNF2FF`, `AnalyzeNF2FF`, `ReadNF2FF`, `CalcSAR`,
`DelayFidelity`), field/HDF5/VTK processing (`ReadHDF5*`, `ReadUI`,
`GetField_*`, `Dump*`, `ConvertHDF5_VTK`, `PlotHDF5FieldData`), queues and
optimization (`InitQueue`, `Add2Queue`, `CheckQueue`, `FinishQueue`,
`ResultsQueue`, `optimize`), and plotting helpers (`plotFF3D`, `plotFFdB`,
`polarFF`, `plotRefl`). The declaration count includes local helpers,
examples, and private functions; it is not a count of supported public APIs.

### Core M-file setup and execution contracts

| Entry point | Source-level contract |
| --- | --- |
| `InitFDTD(varargin)` | Defaults to `NrTS=1e9` and `EndCriteria=1e-5`; accepts legacy positional numeric forms with a warning. Name/value parsing is case-insensitive for `CoordSystem`, `NrTS`, and `EndCriteria`; coordinate system is stored as boolean `CylinderCoords`, while other keys become root attributes. Odd pair counts are not explicitly checked. |
| `SetBoundaryCond(FDTD, BC, varargin)` | Requires exactly six numeric or cell entries and writes xmin/xmax/ymin/ymax/zmin/zmax. Additional pairs are copied to boundary attributes without validating names or even argument count. |
| `AddPML(mesh, numcells, CoordSystem=0)` | Expands a scalar count to six sides or requires exactly six values, sorts/deduplicates each axis, then extends both ends by the first/last cell spacing. `CoordSystem==1` selects `r/a/z`; other values silently use `x/y/z`. It adds mesh space only, not PML boundary conditions. Noninteger/negative counts and axes with fewer than two unique lines are not explicitly validated. MATLAB R2025b confirmed directional padding and zero-count behavior; no direct unit test was found. |
| `AddMRStub(CSX, materialname, prio, MSL_width, len, alpha, resolution, orientation, normVector, position)` | Converts angles from degrees, generates the radial-stub polygon in a local plane, rotates/translates it using the selected normal axis, then delegates to `AddPolygon`. The normal-vector guard uses chained equality comparisons and algebraic sum, then normalizes by that sum and selects the plane only from positive components; it does not reliably enforce exactly one nonzero component or handle negative-axis normals. No direct test or runtime reference was found. |
| `SetGaussExcite(FDTD, f0, fc)` | Sets excitation type 0, center/cutoff frequencies, and `f_max=f0+fc`; no wrapper-side range checks. |
| `SetSinusExcite` / `SetCustomExcite` / `SetDiracExcite` / `SetStepExcite` | Set excitation types 1/10/2/3 respectively; sinus/custom set `f0` and `f_max=f0`, and custom also stores `Function`. Dirac/step add no frequency limit. Inputs are not validated by these wrappers. |
| `InitCylindricalFDTD(NrTS, endCrit, varargin)` | Deprecated compatibility wrapper that warns, forwards legacy positional values to `InitFDTD`, then sets `CylinderCoords=1`. |
| `WriteOpenEMS(filename, FDTD, CSX)` | Wraps the structures as `openEMS.FDTD` and `openEMS.ContinuousStructure`, then calls the shared XML serializer with root `openEMS`. |
| `RunOpenEMS(Sim_Path, Sim_File, opts, Settings)` | Appends `--legacyHDF5Dumps`, changes into `Sim_Path`, invokes local or configured SSH execution, and restores the previous directory only at the normal function exit. Errors after `cd` can leave MATLAB in the simulation directory. |
| `invoke_openEMS(opts, logfile, silent)` | Private launcher that searches development/install locations and then `PATH` for `openEMS.sh` on Unix or the development tree and `PATH` for `openEMS.exe` on Windows. It quotes the executable path but appends `opts` as a preformatted command string. Silent mode redirects output to the log; non-silent Unix mode uses `tee` only when a log argument was supplied, while non-silent Windows mode does not use the log. A nonzero `system` status raises an error. The exact M-file launcher path was not directly exercised; the WSL build and solver tests used other entry points. |
| `setup()` | MATLAB prints that no setup is needed; Octave compiles `h5readatt_octave` and `h5writemode_octave`, locating HDF5 with Homebrew on macOS or `pkg-config`/filesystem fallback on Linux. The non-Unix path invokes `mkoctfile -lhdf5` directly. It changes to the M-file directory and restores the prior working directory only on normal completion, so a compile error can leave the caller in that directory. Octave was available in the later WSL baseline, but the compile-failure/working-directory recovery path was not directly exercised. |
| `ensure_oct_file(fname)` / local `oct_file_usable(fname)` | Octave-only callers use this to invoke an oct-file without arguments and classify it as loadable unless the error text contains `failed to load`. Missing/incompatible files trigger `setup`, then a function clear and a second usability check; setup and final-load failures are raised with `openEMS:ensure_oct_file`. This recovery path was mapped from source but not directly exercised by the available suite. |
| `FindFreeSSH(host_list, Settings, wait_time=600, command='ps -e \| grep openEMS')` | Treats a character input as a host-list filename and otherwise requires a cell array. It builds an SSH or PuTTY command, uses a 10-second connection timeout, and classifies a host as free only for empty output with status 1; nonempty output/status 0 means busy. With `wait_time<=0` it warns and returns empty after one scan; positive values pause and retry indefinitely. No direct tests were found, and network execution was not attempted. |
| `RunOpenEMS_Parallel(Sim_Paths, Sim_Files, opts, Settings, varargin)` | Falls back to serial calls on unsupported OS/single-path/missing host-list cases; otherwise queues one `RunOpenEMS` job per path. The fallback computes each `Sim_File` but passes the original `Sim_Files` argument instead. |

### M-file field, HDF5, and voltage/current data contracts

| Entry point | Source-level contract |
| --- | --- |
| `ReadHDF5Dump(file, varargin)` | Reads field data and mesh, then applies requested operations in a fixed order: `Range`, `SubSampling`, `Interpolation`, `Frequency`, `CloseAlpha`, regardless of argument order. Unknown option names are ignored. Cylindrical `CloseAlpha=1` appends the first angular slice when the angular span is less than `2*pi`; its local `range(x)` helper is `max(x)-min(x)`. |
| `ReadHDF5Attribute(file, groupname, attr_name)` | Reads an HDF5 attribute and converts it to `double`. Octave ensures and calls the compiled `h5readatt_octave`; MATLAB selects `hdf5read` or `h5readatt` based on version thresholds 7.9 and 7.12. No direct tests were found. |
| `ReadHDF5FieldData(file)` / local `ReadHDF5FieldData_octave(file)` | MATLAB reads `/FieldData/TD` datasets and time attributes, then FD frequencies and split-complex datasets with a real-dataset fallback. Its TD attribute-name parsing can produce `1/time`, which is used as an invalid dynamic struct field in MATLAB R2025b on a round-trip written by `WriteHDF5`. Octave loads the HDF5 tree into a struct, strips the leading underscore from numeric TD dataset field names, reads each time attribute through `ReadHDF5Attribute`, and tries split-complex FD data before real-only datasets; failure of both FD layouts raises `openEMS:ReadHDF5FieldData`. No focused Octave fixture probe was recorded; the later WSL Octave suite passed. |
| `ReadHDF5Mesh(file)` / local `ReadHDF5Mesh_octave(file)` | Returns coordinate names, line arrays, and mesh type `0` (Cartesian), `1` (cylindrical alpha/rho reordered to rho/alpha/z), or `2` (phi coordinates reordered). MATLAB reads HDF5 dataset names directly; Octave loads the mesh group into a struct and constructs dataset paths from its field names. A synthetic WSL Octave fixture confirmed Cartesian and spherical labels/order, but exposed a cylindrical mismatch: `fieldnames` returns column-shaped `names`, so `fliplr(names(1:2))` does not swap alpha/rho, while the row-shaped `lines(1:2)` is swapped. The returned names are therefore alpha/rho while the corresponding arrays are rho/alpha. |
| `WriteHDF5(filename, hdf_fielddata, hdf_mesh)` / local `WriteHDF5_octave(...)` | Writes each TD value as `/FieldData/TD/<1-based index>` with a `time` attribute; FD values use separate real/imaginary datasets plus a frequency group attribute; mesh names and lines are appended. The Octave helper immediately errors with `not yet implemented`. MATLAB R2025b FD values and mesh coordinates round-trip; HDF5 vector axes are returned as columns and should be compared by values, not orientation. |
| `h5writemode(filename, x, y, Vx, Vy)` | Writes `/x`, `/y`, `/Vx`, `/Vy` and root `Version=1.0` for waveguide-port mode files. MATLAB transposes component matrices to account for HDF5 dimension reversal; Octave delegates to `h5writemode_octave`, which requires `nx`-by-`ny` matrices and writes C-row-major datasets. The MATLAB branch relies on HDF5 calls for dimension errors; the Octave C++ helper checks component shapes but does not check all HDF5 write return statuses. No dedicated unit test was found. A MATLAB R2025b focused probe confirmed coordinate values, transposed component data as seen by `h5read`, and the root version attribute; the Octave variant was not directly probed, although the later WSL Octave suite passed. |
| `ReadUI(files, path, freq, varargin)` | Loads whitespace-delimited text where columns 1–2 are time and signal and later columns are retained as `additional`. With no frequencies it uses FFT; otherwise it uses DFT or optional AR estimation. `AR='auto'` doubles order after error code 11; other AR failures warn and fall back to DFT. Periodic signals reject AR and warn when FFT is requested. |
| `AR_estimate(t, val, freq, nu=40, mu=3*nu, expand_factor=5)` | Requires equal input element counts, `mu>2*nu`, `expand_factor>1`, and a record length of at least `0.6*mu`; depending on requested outputs, these return error codes 1/2/3/10 or throw. It fits an autoregressive least-squares model from the final `mu` samples, extrapolates to `expand_factor*numel(t)`, and returns error 11/throws when the positive maximum exceeds the original maximum. Sampling interval is taken only from `t(2)-t(1)`; integer orders, uniform timing, and nonempty inputs are not validated. MATLAB R2025b confirmed constant-signal continuation and error codes 1, 2, 3, and 10; error 11 and nonuniform sampling remain untested. |
| `FFT_time2freq(t, val)` | Uses `dt=t(2)-t(1)`, zero-pads to the next power-of-two length, scales the FFT by `dt`, returns the nonnegative half-spectrum doubled for single-sided output, and corrects phase by `t(1)`. It does not validate matching lengths, uniform time spacing, or at least two samples. The pure-M-file `transforms` group compares it with an analytic Gaussian spectrum, with `DFT_time2freq`, and after truncating leading quiet samples. |
| `calc_ypar(f, ports, Sim_Path_Prefix)` | Reshapes `f` to a row, allocates NaN matrices sized by the maximum port number, and for each excitation run reads each port's U/I files. MSL current is averaged across two probes; other ports use one current probe. It DFTs U/I, corrects the half-time-step H-field advance, then computes each frequency slice using matrix right-division `I/U`. It assumes valid port numbers, complete simulation files, and compatible data; no direct tests were found. |
| `harminv(timeseries, timestep, start_freq, stop_freq)` | Invokes external `harminv` through a shell command, choosing Unix `export LD_LIBRARY_PATH=; harminv` or a Windows executable in the parent of the M-file directory. It transposes row input, writes a temporary signal file, parses comma-separated output after the first line, filters negative frequencies, and doubles amplitudes. All-zero input prints and returns early; temporary-file cleanup, input validation, and process-failure outputs are not handled explicitly. No test was found; the executable is absent from `PATH` and its expected Windows path, so end-to-end behavior was not run. |
| `GetField_Range(field, mesh, range)` | Slices each of three coordinate axes and all TD/FD field arrays by selected indices, storing original mesh indices. Empty axis ranges retain all points; a two-element range includes mesh points inside both bounds; a one-element range searches for the first mesh point at or above the value. If no point matches, its fallback indexes a nonexistent second range value; MATLAB R2025b confirmed an `Index exceeds the number of array elements` error for a scalar request above the mesh maximum. |
| `GetField_SubSampling(field, mesh, subsampling)` / local `subsample_fields(field, ss_idx)` | Selects indices `1:step:n` independently for the three axes; the local helper slices each value array as `values{n}(ss_idx{1},ss_idx{2},ss_idx{3},:)`. Original indices are composed when present. Requires numeric input with three elements but does not validate positive integer steps. TD/FD metadata is reconstructed selectively rather than copied wholesale. |
| `GetField_Interpolation(field, mesh, lines)` / local `interpolate_fields(field, x, y, z, x_i, y_i, z_i)` | Accepts three target counts (`0` preserves an original axis) or three target-coordinate arrays (empty preserves an axis); applies MATLAB `interpn` to each sample and propagates time/frequency metadata. The local helper has separate 2-D paths for singleton source axes; vector handling assumes three components when the component dimension exceeds one. |
| `GetField_TD2FD(field, freq)` | Computes each frequency by summing TD samples with `exp(-1i*2*pi*f*t(n))*2*dt`, where `dt` comes only from the first two timestamps; marks the result complex and preserves TD data. Missing TD data warns and returns unchanged; fewer than two time samples or nonuniform sample spacing is not explicitly handled. |
| `Dump2VTK(filename, fields, mesh, fieldname, varargin)` | Writes ASCII VTK rectilinear Cartesian or structured cylindrical/spherical grids. By default, cylindrical/spherical vectors are converted to Cartesian; `NativeDump` retains native components, and `CloseAlpha` repeats the first angular slice for an incomplete full revolution. NaN/Inf field values are replaced by zero. An analytic MATLAB probe confirmed the spherical Cartesian Y-component conversion drops the radial contribution at azimuth `pi/2` (a unit radial vector at theta/phi `pi/2` is emitted as approximately zero rather than +Y). |
| `DumpFF2VTK(filename, farfield, thetaRange, phiRange, varargin)` | Writes an ASCII VTK structured grid with one radial point per theta/phi sample; `scale` changes point radius but not the scalar gain. Optional `logscale` computes `20*log10(farfield)+maxgain-logscale`, clamps negative values to zero, and is added back to the saved scalar data. NaN/Inf values are replaced with zero after the optional logarithm; output file opening and field/range dimensions are not explicitly validated. No direct tests were found. |
| `ConvertHDF5_VTK(hdf_file, vtk_prefix, varargin)` | Defaults to FD dumps on, TD dumps off, 36 phase samples, unit weighting, and field name `unknown`. Complex FD emits phase, magnitude, and angle files per frequency; real FD emits one file per frequency; TD emits absolute-valued samples. Remaining options are also forwarded to `ReadHDF5Dump` and `Dump2VTK`. |
| `PlotHDF5FieldData(file, PlotArgs)` | Reads TD data, plots a selected component or vector magnitude, defaults pause to 0.01 seconds, and permutes Cartesian field axes for MATLAB plotting. It reports unsupported non-Cartesian mesh types but continues into the Cartesian plotting path; required `component` and slice fields are not validated. |
| `AddLumpedPort(CSX, prio, portnr, R, start, stop, dir, excite, varargin)` | Requires exactly one nonzero direction component and nonzero extent along it. Finite positive resistance creates a lumped element, nonpositive resistance creates a metal, and positive infinity creates neither. Active ports add an excitation; voltage/current probes are placed on planes derived from the box and accept separate weight options. Character `excite` values are retained as a deprecated truthy/nontruthy convention. |
| `AddMSLPort(CSX, prio, portnr, materialname, start, stop, dir, evec, varargin)` | Requires a defined rectilinear mesh, derives propagation/width/height axes from `dir` and `evec`, places voltage/current probes against sorted mesh lines, and optionally adds excitation/resistance. Several option names are case-sensitive. The source's chained equality check for `evec` is not a reliable exactly-one-nonzero test. MATLAB R2025b confirmed that legacy `ExcitePort=''` enables excitation because the branch tests the default boolean rather than the supplied string; the same source branch appears in `AddCPWPort` and `AddStripLinePort`. |
| `AddStripLinePort(CSX, prio, portnr, materialname, start, stop, height, dir, evec, varargin)` | Builds two offset stripline sheets, six weighted voltage probes (three longitudinal positions on each sheet), and two current probes. `height` offsets the two sheets; finite positive `Feed_R` uses twice the requested resistance across both sheets, zero uses metal, and infinity leaves the feed open. The returned type is handled by `calcTLPort`. |
| `AddCPWPort(CSX, prio, portnr, materialname, start, stop, gap_width, dir, evec, varargin)` | Builds two signal/gap-side sheets, six voltage probes, and two current probes; `gap_width` offsets the paired sides. Finite positive `Feed_R` uses twice the requested resistance across the paired feeds, zero uses metal, and infinity leaves the feed open. The returned type is handled by `calcTLPort`. |
| `AddWaveGuidePort(CSX, prio, portnr, start, stop, dir, E_WG_func, H_WG_func, kc, exc_amp, varargin)` | Requires a grid and paired mode functions or paired mode files. Nonzero excitation amplitude adds a source at the start plane; voltage/current mode probes are placed at the stop plane. Supports a Cartesian `local_origin` vector or Cartesian-only `corner`/`center` shorthand; it rejects those shorthands for cylindrical grids. |
| `AddRectWaveGuidePort(CSX, prio, portnr, start, stop, dir, a, b, mode_name, exc_amp, varargin)` | Supports TE mode names, derives cutoff wavenumber from rectangular dimensions, builds analytic mode functions and delegates to `AddWaveGuidePort` with `local_origin='corner'`. Its secondary mesh-line validation is nested after an unconditional missing-grid error and therefore cannot run. |
| `AddCircWaveGuidePort(CSX, prio, portnr, start, stop, radius, mode_name, pol_ang, exc_amp, varargin)` | Supports a fixed table of TE mode/Bessel-root pairs, creates radial/azimuthal analytical fields, and delegates to `AddWaveGuidePort`. Cartesian meshes use the box center as local origin; cylindrical meshes use native rho/alpha coordinates without a shift. |
| `AddCurvePort(CSX, prio, portnr, R, start, stop, excite, varargin)` | Snaps endpoints to nearest grid lines, chooses the longest coordinate span as the port axis, and builds the required metal/probe/excitation boxes. A finite positive `R` creates a lumped element; `R==0` reuses the metal segment; negative/NaN resistance has no explicit termination branch. The returned type is `Lumped`, accepted by `calcPort`'s lumped branch. |
| `AddCoaxialPort(CSX, prio, portnr, pec_name, materialname, start, stop, dir, r_i, r_o, r_os, varargin)` | Adds inner conductor and outer shell, optionally fills the annulus, positions three voltage and two current probes from the mesh, and can add an analytic radial excitation. Positive finite `Feed_R` errors as unimplemented; infinity leaves an open feed, zero adds a metal termination, and negative resistance errors. |
| `calcPort(port, SimDir, f, varargin)` | Recurses over cell arrays, dispatches MSL/coaxial/stripline/CPW to `calcTLPort`, waveguide to `calcWGPort`, and lumped/curve to `calcLumpedPort`; adds incident/reflected/accepted power from the returned frequency-domain voltage/current waves. |
| `calcWGPort(port, SimDir, f, varargin)` | Reads U/I text outputs, calculates `beta=sqrt(k^2-kc^2)` and analytic waveguide impedance, then separates incident/reflected waves. Its `RefPlaneShift` branch computes the phase using bare `beta` rather than `port.beta`; MATLAB R2025b resolves this name to the built-in beta function and raises “Not enough input arguments.” |
| `calcTLPort(port, SimDir, f, varargin)` | Reads transmission-line U/I probe files, averages adjacent current probes, estimates propagation constant and impedance from sampled spatial derivatives, optionally shifts the reference plane, then separates incident/reflected waves. It warns when its two voltage spacings are not equidistant. |
| `calcLumpedPort(port, SimDir, f, varargin)` | Reads U/I probe files, computes `Zin=U/I`, and separates waves using `Feed_R` by default or an explicit `RefImpedance`; `SwitchDirection` changes current sign. Zero/infinite impedances and division-by-zero samples are not explicitly validated. |
| `CreateNF2FFBox(CSX, name, start, stop, varargin)` | Creates six E/H dump-plane pairs in fixed negative/positive x/y/z order, with `Directions` flags to omit faces and optional dump arguments forwarded to `AddDump`. `Frequency` changes dump type to frequency-domain; otherwise dumps are time-domain. |
| `CalcNF2FF(nf2ff, Sim_Path, freq, theta, phi, varargin)` | Writes an nf2ff XML request in legacy HDF5 mode, discovers E/H plane files by wildcard and list position, and either reads cached results or invokes the `nf2ff` executable. Cache reuse checks frequency/theta/phi vectors using a relative `1e-6` comparison. The external `system` return status is not checked before attempting result readback; a failed run can leave a stale output eligible for readback if its axes match. |
| `vectorEqual(v1, v2, acc=1e-6)` (local to `CalcNF2FF.m`) | Returns false when element counts differ; otherwise evaluates `abs((v1(:)-v2(:))/v1(:)) > acc` using MATLAB matrix right-division on two column vectors. This produces an `N x N` matrix; `sum` then reduces it by column, and the resulting vector `if` condition only takes the mismatch branch when all column flags are true. Consequently, a mismatching column can be ignored if another column has no over-tolerance entries. A MATLAB R2025b arithmetic probe reproduced this with `v1=[1;1]`, `v2=[2;0]`; the expression accepted them. Used for cached frequency/theta/phi axes; no direct helper test was found. |
| `ReadNF2FF(nf2ff)` | Reads radius/theta/phi axes, frequency/power/directivity/material attributes, and split-real/imaginary legacy or compound-complex fields. It normalizes result axes to theta/phi, derives field magnitude and RHCP/LHCP, and rejects compound-complex data in Octave. |
| `ReadComplexFD(file, dataset)` (local to `private/ReadNF2FF.m`) | Reads the compound dataset with `h5read`, converts its `r` and `i` fields to double, and transposes the result into the reader's theta/phi convention. Missing fields, unsupported dataset types, and shape mismatches propagate from HDF5/field access; no dedicated M-file fixture test was found. |
| `AnalyzeNF2FF(Sim_Path, nf2ff, f, theta, phi, r)` | Deprecated single-frequency Matlab near-to-far calculation over enabled planes; theta/phi are degrees and radius is documented as optional with default 1 m. The implementation requires exactly six inputs and does not default `r`; MATLAB R2025b confirmed calling without it raises “Not enough input arguments.” |
| `process_plane(k, n, center, mesh, E_field, H_field, theta, phi)` / local `dbltrapz(matrix,a,b)` | For axis-aligned unit normal `n`, selects one field plane, forms equivalent electric/magnetic surface currents, applies the far-field phase term, and integrates theta/phi components over the two mesh axes. Radiated power is computed only when requested. Although `center` is documented as an antenna-center correction, it is not referenced in the helper body. `dbltrapz` applies `trapz` successively and requires column coordinate vectors; neither helper validates dimensions or degenerate mesh axes. No direct unit tests were found. |
| `CalcSAR(sar_fn, sar_out, varargin)` | Builds a `sar_calc` command with legacy HDF5 enabled and maps mass, averaging method, auto-range, threads, verbose, and progress options. It does not check the returned `system` status, so a nonzero process exit may appear successful; caught errors are replaced by generic `CalcSAR: failed`. |
| `InitQueue(varargin)` / `Add2Queue(queue, func_name, func_args, varargin)` | Queueing is Unix-only. Defaults to Octave when running there, uses unlimited `MaxThreads`, and serializes each argument list to a temporary MAT file before launching a child interpreter. `Add2Queue` derives output count with `nargout(func_name)` and catches child errors for later reporting. Option names are exact-case. |
| `CheckQueue(queue, query_time=5)` / `FinishQueue(queue, query_time=5)` | Polls process helpers after a pause; completed jobs load serialized results/errors, raise `CheckQueue:<message>` on child exceptions, collect stdout/stderr, and delete argument/result files. `FinishQueue` polls until no jobs remain. |
| `queue_addProcess(command)` / `queue_checkProcess(pid, filenames)` / `queue_delProcess(pid, filenames)` | All reject non-Unix platforms. Add launches a shell group in the background and parses the echoed PID; it captures output to temp files only when more than one output is requested, otherwise redirects to `/dev/null`, and ignores shell status. Check optionally reads the capture files before running `ps --no-headers -p<PID>`; `alive` is status zero, and file-open failures are unchecked. Delete skips signaling for PID 0; otherwise it tries TERM, checks immediately, waits one second before a second TERM, then escalates to KILL if still alive. It optionally reads and deletes capture files but does not validate kill status or recheck after KILL. No direct process-helper tests were found; the Windows host cannot execute these paths. |
| `ResultsQueue(queue, n)` | Returns stored job outputs and checks only that the requested index exists and the caller did not request more outputs than the job produced; it does not check that the job has finished. |
| `optimize(optimdir, params, options, algorithm)` | The default `simplex-downhill` branch always errors as unimplemented; `asco` writes ASCO configuration/scripts and reads `best_result.mat`. The ASCO branch does not check process status before loading results; `folder_matlabstart` path generation references `functions.folder_matlabstart` instead of `options.folder_matlabstart`. Directory restoration is not protected against intermediate errors. |

### M-file plotting and cleanup contracts

| Entry point | Source-level contract |
| --- | --- |
| `plotFF3D(nf2ff, varargin)` | Defaults to frequency index 1, linear field magnitude, and no normalization. `normalize` or `logscale` first divides by the maximum field value; logarithmic mode maps the requested dB floor to the plot origin and clamps lower values to zero. It plots a spherical surface colored by field magnitude and labels the colorbar against `Dmax`. Option pairs are case-sensitive; odd argument counts, invalid frequency indices, zero maxima, and invalid log scales are not explicitly validated. |
| `plotFFdB(nf2ff, varargin)` | Defaults to frequency index 1, `phi` as the x-axis, and parameter index 1. It normalizes `E_norm`, converts to dBi using `Dmax`, and plots a theta or phi slice with legends derived from the complementary angle. Unknown axes raise an identified error; indices, dimensions, and zero field maxima are not checked. |
| `polarFF(nf2ff, varargin)` | Defaults to frequency index 1, `phi` as x-axis, parameter 1, linear unnormalized magnitude, and five radial ticks. When `logscale` is supplied, it maps dB magnitudes to a radial scale; a two-value range rescales to the supplied maximum. Otherwise `normalize` divides by maximum magnitude. It draws its own polar grid and slice legend. This differs from the header's stated default logscale of -20 dB: source default is empty/linear. Invalid axes raise an error; log range order, zero maxima, index bounds, and extra/missing option values are unchecked. |
| `plotRefl(port, varargin)` | Requires `port.uf` and plots `uf.ref ./ uf.inc` on a generated normalized Smith chart. Defaults are zero decimal places, -3 dB threshold, and automatically detected strict threshold crossings; optional `fmarkers` selects nearest frequency samples. It marks lower/upper crossings and minimum reflection, then builds a legend with frequencies in MHz. Missing crossings can fail when indexing the empty crossing set; zero incident waves and malformed marker vectors are not validated. Unknown options warn with the `openEMS:polarFF` identifier. No plotting fixtures or GUI tests were found. |
| `CleanupSimPath(Sim_Path, verbose=0)` | Removes a fixed whitelist of excitation/port text files, NF2FF-named HDF5, VTK-family files, stats, and `debugCSX.xml`; it then inspects remaining `.h5` files and deletes those with the root `openEMS_HDF5_version` attribute or `/nf2ff/Frequency`. The attribute probes are wrapped in broad catches because a failed probe means “not this file type”; unrelated HDF5 files are retained. Directories are skipped, optional verbose output names deleted files, and a missing simulation directory is created afterward. A focused WSL Octave probe confirmed deletion of listed outputs, preservation of unrelated files including an unreadable `.h5`, and creation of a missing directory. Actual openEMS HDF5 fingerprint deletion and mixed user/openEMS artifacts remain untested. |

### M-file optimizer and example workflows

| Entry point | Source-level contract |
| --- | --- |
| `optimizer_simfun(folder, params)` | Example ASCO callback that builds a fixed 50 MHz coil model in `folder`, runs openEMS, reads port voltage/current spectra, estimates inductance, and returns the absolute difference from a 2 uH target as a nonnegative cost. A zero-argument call selects a visualization path, but returns after `CSXGeomPlot` without restoring the working directory. Normal execution also restores the directory only on success. |
| Local `structure(params, filename, f_max)` / `create_coil(...)` / `postproc(filename, f_max)` | Builds a helical curve with `params.turns`, meshes and ports it, optionally writes FDTD/XML when a filename is supplied, samples port U/I across 200 non-DC frequencies, and computes `imag(U/I)/(2*pi*f)`. `create_coil` defaults resolution to 30, winding/direction to +1 and offset to zero; zero turns, nonpositive dimensions, and invalid vectors are not explicitly checked. |
| `optimizer_asco_sim(optimdir, inputfile, outputfile, simfun)` / local `create_folder_name(params)` | ASCO callback that changes into `optimdir`, loads its generated `params` script (renaming dash-containing input files temporarily), and uses a parameter-derived directory plus `result.mat` as a cache. Cache misses invoke the selected simulation function and save its result; it writes the ASCO output record and updates `best_result.mat` when the cost improves. Directory/file restoration and output-file checks are not protected against failures. The local folder key sorts parameter fields but uses `num2str` values without a collision-resistant encoding. |
| `directional_coupler` / local `sim`, `postprocess`, `smithchart`, `y2s` | Four-run microstrip directional-coupler example: each run excites one of four curve ports, writes XML, optionally runs the solver, and post-processing computes Y parameters then converts them to S parameters using `(I+Y) \ (I-Y)`, where `I` is the identity matrix divided by the default `ZL=50`. The Smith chart uses an external `smith` function when present and otherwise draws a simple chart. The source assigns PML boundaries and then replaces them with MUR boundaries. Simulation/plotting was not executed. |
| `CreateCRLH(CSX, mesh, CRLH, resolution, translate=[0,0,0])` | Adds top/bottom metal patches and two via cylinders for a CRLH unit cell, appending geometry-aligned mesh hints and translating geometry. It assumes all named `CRLH` fields and valid mesh vectors are supplied; no shape or range validation is present. |
| `Patch_Antenna_Array(Sim_Path, postproc_only, show_structure, xpos, caps, resist, active)` | Builds a reactive-loaded patch array, per-element capacitive loads or lumped ports, a lossy substrate, smoothed mesh, NF2FF box, and PML. When `postproc_only==0`, it cleans the simulation path, writes XML, optionally opens the GUI, and runs the solver; all arguments are required and array lengths are not checked against `xpos`. No direct tests were found. |
| Local `absolutepath(folder)` in `optimize` | Returns absolute Unix/Windows paths unchanged or joins relative paths to `pwd`; rejects Windows drive-relative forms. It indexes path characters without first checking length or emptiness, and its behavior was not directly tested. |

The declaration cross-check accounts for all 96 openEMS M-file function names
and all 48 distinct non-private Python-visible `def`/`cpdef` names across
these contract tables and the component-specific sections above. This is
source/API coverage, not exhaustive edge-case validation; test maps and
native/reference behavior remain incomplete.

Two source discrepancies need reference confirmation: the fallback branch in
`RunOpenEMS_Parallel` computes a per-run `Sim_File` but appears to pass the
original `Sim_Files` value to `RunOpenEMS`; and the remote SSH error path
prints a prior `result` variable rather than the failing command's `res`.
The default end-criteria documentation also differs between the Python
constructor (1e-5) and the C++ reset default (1e-6). These are recorded as
compatibility questions, not verified behavior defects. The MATLAB R2025b
HDF5 TD reader failure and the unimplemented Octave HDF5 writer are separately
recorded in the findings and validation records.

## Initial execution attempt (superseded in part by the WSL baseline)

The MATLAB `TESTSUITE` runner listed the MATLAB unit, probe, combined,
NF2FF, and engine-comparison tests. Its two pure-M-file unit groups passed 17
checks in 2.3 seconds; details are in `audits/openems-core.md`. The solver
executable was absent, so the MSL notch-filter solver smoke, full simulation
suite, and `RunOpenEMS` were not executed. No Python extension import or
solver output was available for an end-to-end workflow. Additional MATLAB
in-memory probes verified range selection, subsampling, linear interpolation
of an analytic scalar field, and the discrete TD-to-FD sum; a separate
boundary probe reproduced the scalar out-of-range indexing error described
above.

The Python runner in `python/Tests/run_testsuite.py` separates `test_*.py`
unit tests from simulation scripts; it supports listing/filtering, timeouts,
and per-test temporary directories. The ten unit modules cover controller
configuration/XML (`test_openEMS.py`, `test_XML_RoundTrip.py`), port
construction/compatibility (`test_Ports.py`), mesh hints (`test_Automesh.py`),
HDF5 layouts/regions (`test_hdf5_utils.py`), NF2FF file formats
(`test_nf2ff.py`), SAR calculation/readback (`test_SAR_Calculation.py`,
`test_sar_analytic.py`, `test_sar_utils.py`), and test-script hygiene
(`test_sim_scripts.py`). The other scripts are full simulation references for
ports, field probes, materials, NF2FF, SAR, and cylindrical cases. The runner
was run on 2026-10-16 with `--only-unittests --timeout=30`:
`test_sim_scripts.py` passed and nine tests errored during import. Eight could
not import NumPy and
`test_SAR_Calculation.py` could not import the `openEMS` package. This initial
Windows attempt ran before dependencies were installed and is superseded by
the later WSL results in `../VALIDATION.md`: the full Python unit/simulation
suite and Octave suite passed there, and both documented smoke tests passed.
Individual untested paths below remain open.

## Remaining compatibility work

- Complete per-method accounting of Python and M-file argument validation,
  defaults, exceptions, array/string conversions, and numerical behavior;
  the inventory above is not a substitute for that contract-level map.
- Verify Python progress/cancellation, reset/ownership, setup/runtime error
  propagation, and working-directory effects against an installed native
  library.
- Differentially verify port geometry/mode/impedance calculations, HDF5
  field selection and legacy layouts, NF2FF, SAR, and Matlab/Octave parity.
- Confirm the `RunOpenEMS_Parallel` argument and remote-error behavior with
  executable references before classifying either source discrepancy.
- Compare representative Matlab/Octave and Python setup, excitation, port,
  field dump, NF2FF, and HDF5 workflows after the native stack is installed.
