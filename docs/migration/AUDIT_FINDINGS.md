# Consolidated Migration Audit Findings

This is a cross-component index, not a replacement for the evidence and
limitations in the component audits. “Confirmed” means observed in source or
an executed reference probe; it does not imply a decision to preserve or fix
the behavior. No submodule implementation was changed.

Runtime limitations in the component notes below refer to the environment and
tests available during their initial source audits unless stated otherwise.
The later WSL baseline ran the principal native-backed suites; the exact
results and the remaining path-specific gaps are recorded in `VALIDATION.md`.

## Confirmed source findings and observable limitations

| Component | Finding | Evidence |
| --- | --- | --- |
| fparser | `AddFunctionWrapper` has a failure path that leaks its copied wrapper. Optimizer probes also showed observable callbacks and invalid-operation errors can be removed. A public documentation/type mismatch is separately recorded. | [fparser audit](audits/fparser.md) |
| CSXCAD native | `GetPrimitivesByType` is declared but logs “not yet implemented” and returns an empty vector. XML reading clears first, may continue after a parameter warning, and skips unknown property tags; file writing changes the process numeric locale without restoring it. | [native audit](audits/csxcad-native.md) |
| CSXCAD Python | The primitive wrapper factory raises for `USERDEFINED`; wrapper identity, ownership, and invalidation callbacks are observable API behavior. `GetMultiDirs` has no invalid-string error branch, and `CSPrimMultiBox.GetBox` has no negative-index guard. Seven targeted wrapper-cache tests passed in WSL; a stale test comment claiming there is no structure destructor conflicts with the current `ContinuousStructure.__dealloc__` source. The other items are source observations, not verified defects. | [interface audit](audits/csxcad-interfaces.md) |
| CSXCAD Matlab/Octave | `AddProbe`'s unknown-option warning formats the option value instead of the key, `CheckMesh` quiet mode suppresses returned error details as well as warnings, and the Virtual Family converter's unknown-option branch fails on misspelled `varagin` (all reproduced in MATLAB). Source also uses `dx` for converted Y/Z mesh endpoints. Exporters have source-observed option/field mismatches: Empire's optional-argument default and polygon normal access, Excellon's cylinder helper call, Gerber's undefined header variable, and POV-Ray's `P0` field. WSL Octave confirmed the XML writer emits raw ampersands and empty elements, and raises at `fprintf` after an unchecked `fopen` failure. | [interface audit](audits/csxcad-interfaces.md), [validation](VALIDATION.md) |
| Root build | Python site-mode arguments are appended to a misspelled variable, so the requested option is not passed. The 2026-10-16 offline WSL build reproduced this: the generated venv lacked system site packages and Python metadata preparation failed because `setuptools` was unavailable. A manually created venv worked around the failure without source changes. `update_openEMS.sh` error handling also discards the specific failure message. | [root orchestration audit](audits/root-orchestration.md), [validation](VALIDATION.md) |
| CTB | `a_PI` fails for numeric inputs; 3+ port Touchstone ordering is transposed; malformed extensions and malformed/truncated records can be accepted; parse errors leave input files open; singular/non-finite inputs often propagate. `Y_se` is documented but `Y_sh` is implemented. | [CTB audit](audits/ctb.md) |
| hyp2mat | QucsStudio export warns about but omits stackup layers after the first. The README claims QucsStudio input, while inspected parser sources expose HyperLynx input and QucsStudio output only. | [hyp2mat audit](audits/hyp2mat.md) |
| openEMS SAR | SAR requires cell interpolation, rejects raw output unless HDF5 is used, ignores subsampling with a warning, and warns that anisotropic material is unsupported. | [processing audit](audits/openems-processing.md) |
| openEMS scripting | Python `Run` changes the process-wide current directory without restoring it; a nonzero setup code is printed and returned rather than raised. Python `SetBoundaryCond` forwards integer values without enum-range validation despite a six/eight-entry doc mismatch. `LumpedPort` has no negative-resistance branch before using its load variable; `CurvePort` has no negative-resistance branch; their reference-plane warnings are constructed but not emitted; and `mesh_combine` ignores its `sort` argument when both meshes are set. Coaxial finite positive termination resistance raises `NotImplementedError`. M-file `RunOpenEMS_Parallel` fallback passes the original file collection instead of the per-run filename, and its SSH failure path reports a stale variable; both remain runtime-unconfirmed. Source review also found optimizer callbacks restore their working directory only on normal completion; the no-argument visualization path of `optimizer_simfun` exits without restoring it. `setup()` likewise restores its working directory only on success, while `invoke_openEMS` uses non-silent log redirection only on Unix; these specific paths were not directly exercised by the later suites. | [interface audit](audits/openems-interfaces.md) |
| openEMS Matlab/Octave HDF5 | In MATLAB R2025b, `ReadHDF5FieldData` fails on TD data written by `WriteHDF5`: the HDF5 metadata exposes the attribute name as `1/time`, which is used as an invalid dynamic struct field name. `WriteHDF5_octave` is explicitly unimplemented. FD and mesh values round-trip in MATLAB, with vector orientation returned as columns. Source review also found the Octave mode-file writer does not check all HDF5 write return statuses; this was not runtime-tested. A focused MATLAB `h5writemode` probe passed for coordinates, component data, and the root version attribute. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Octave HDF5 mesh | `ReadHDF5Mesh` reports cylindrical mesh type 1 but returns `names` ordered alpha/rho while its corresponding `lines` arrays are reordered rho/alpha. A synthetic WSL fixture confirmed the mismatch; Cartesian and spherical ordering matched. Source cause: `names` is column-shaped from `fieldnames`, so `fliplr(names(1:2))` is a no-op, while the row-shaped `lines` is reversed. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab VTK | `Dump2VTK`'s spherical-to-Cartesian vector conversion omits the radial contribution to the Cartesian Y component. A MATLAB R2025b probe with a unit radial vector at theta=phi=90 degrees emitted a zero vector instead of +Y. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab field processing | `GetField_Range` errors when a single-coordinate request is above the maximum mesh value: its fallback accesses the missing second range element. This was reproduced in MATLAB R2025b. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab waveguide port | `calcWGPort`'s `RefPlaneShift` branch uses bare `beta` instead of the computed `port.beta`; in MATLAB R2025b the name resolves to the built-in Beta function and errors with “Not enough input arguments.” | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab transmission-line ports | `AddMSLPort(...,'ExcitePort','')` enables excitation instead of disabling it. MATLAB R2025b reproduced this branch; the same source pattern is present in `AddCPWPort` and `AddStripLinePort`. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab NF2FF | `AnalyzeNF2FF` documents `r` as optional with a 1 m default, but its argument check requires all six inputs and no default is assigned. MATLAB R2025b reproduced “Not enough input arguments” when called without `r`. | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| openEMS Matlab CLI wrappers | Source review found `CalcNF2FF` and `CalcSAR` ignore external `system` exit status. A failed NF2FF run may proceed to read a stale output if present; SAR may return without signaling a nonzero executable result. These paths were not runtime-tested. | [interface audit](audits/openems-interfaces.md) |
| openEMS Matlab queue/optimizer | Source review found `optimize` defaults to an unimplemented `simplex-downhill` branch; its ASCO `folder_matlabstart` command uses `functions.folder_matlabstart`, and it does not check ASCO's process status before reading results. `ResultsQueue` also does not require the job to be complete. These paths were not runtime-tested. | [interface audit](audits/openems-interfaces.md) |
| openEMS NF2FF binding | Direct scalar inputs to `_nf2ff.__cinit__` hit `list(float(value))`, which raises `TypeError`; the normal `nf2ff.CalcNF2FF` wrapper normalizes scalars before calling it. Missing H-file errors identify the E filename. | [interface audit](audits/openems-interfaces.md) |
| QCSXCAD | Discrete-material rendering accessors read/write the edit-mode flag instead of the dedicated render flag. Grid update code uses the X plane slider index for Y and Z plane labels. | [GUI audit](audits/gui.md) |

## Compatibility questions requiring reference evidence

| Area | Question | Evidence |
| --- | --- | --- |
| fparser | Which generated optimizer rewrites and optional MPFR/GMP behaviors are compatibility requirements? What cross-compiler numerical differences are accepted? | [fparser audit](audits/fparser.md) |
| CSXCAD | What are the exact subclass copy, XML locale/error/partial-read, null-node, and wrapper invalidation contracts? Is the empty `GetPrimitivesByType` implementation an intentional limitation? | [native audit](audits/csxcad-native.md), [interface audit](audits/csxcad-interfaces.md) |
| openEMS | What are the required extension equations and deterministic solver criteria? What field units/scaling and HDF5/VTK/NF2FF/SAR outputs are the reference contract? | [core audit](audits/openems-core.md), [processing audit](audits/openems-processing.md) |
| openEMS scripting | Which default values are normative where wrapper documentation and C++ defaults differ? What are Python progress/cancellation and exception semantics? What is the intended boundary-condition value validation? How should invalid port resistance and unsupported reference-plane shifts behave? Should `mesh_combine(sort=False)` preserve insertion order, and what probe-header, sample-grid, and relative-zero validation is required? What should M-file parallel fallback and SSH failure reporting do? Is Octave HDF5 writing intentionally unsupported, and what TD attribute metadata and vector-orientation behavior must replacements preserve? What HDF5Dump time-step-uniformity, fractional-sampling, and range-bound semantics are required? What selection/iteration output shapes and malformed-attribute behaviors are normative? What is the intended behavior for scalar field ranges outside the mesh and spherical VTK vector conversion? Should the waveguide mode wrappers enforce paired inputs and mesh-axis validation? Should MSL/CPW/stripline constructors enforce exactly one nonzero excitation-vector component and how should legacy string `ExcitePort` values be interpreted? Should the documented optional radius in deprecated `AnalyzeNF2FF` be restored, and how must NF2FF/SAR CLI failures be surfaced? What queue/optimizer defaults and process-exit/error semantics are required? Should Octave oct-file auto-rebuild and working-directory failure behavior be preserved, and what are the intended local solver logging semantics across Windows and Unix? | [interface audit](audits/openems-interfaces.md) |
| openEMS Octave mesh output | Should the Rust migration return cylindrical mesh names aligned with the rho/alpha line arrays, correcting the confirmed Octave mismatch, or preserve that legacy result shape? | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |
| CSXCAD interfaces | Which unimplemented or unsupported Python/M-file entry points are intentionally out of scope, and which must be maintained for compatibility? Should invalid `GetMultiDirs` input return `None` or raise, and what should negative `CSPrimMultiBox.GetBox` indices do? Should `ReadFromXML` accept `Path` inputs like `Write2XML`, should `DefineGrid` mutate the caller's mapping when smoothing, and should extra positional `ContinuousStructure` arguments be accepted? The coordinate-priority wrapper also discards the native primitive out-parameter; confirm whether that is intentional. Should empty MATLAB/Octave fields serialize identically, and what are the required Octave escaping/error semantics? Should `CheckMesh` quiet mode still return error details, should `AutoSmoothMeshLines`'s `force_min_res` option enforce minimum resolution, should the `AddProbe` warning report its option key, and should the converter's `varagin`/`dx` and exporter mismatches be corrected? | [interface audit](audits/csxcad-interfaces.md) |
| GUI | Does Save As change the future Save target? Should saving a loaded openEMS wrapper preserve FDTD settings? Does nested XML root discovery support all nesting shapes? | [GUI audit](audits/gui.md) |
| hyp2mat | Is QucsStudio input supported, and what is the expected output when a board has multiple stackup layers? | [hyp2mat audit](audits/hyp2mat.md) |
| CTB | Which documented/implemented element type spelling is required, and which singular/domain behaviors should be preserved versus corrected? | [CTB audit](audits/ctb.md) |
| openEMS resource lookup | Should Python's bundled/source/environment-prefix search and MATLAB's function-relative lookup remain intentionally different? Should `get_resource_path` reject absolute or parent-relative segments, and what path validation should `openEMS_resource_path` apply? | [interface audit](audits/openems-interfaces.md) |
| openEMS M-file helpers | Should `AddPML` validate noninteger/negative counts and coordinate-system values, how should `AddMRStub` validate signed single-axis normals, and what finite retry policy should `FindFreeSSH` use? | [interface audit](audits/openems-interfaces.md) |
| openEMS deprecated NF2FF helpers | Should `vectorEqual`'s matrix right-division comparison and `process_plane`'s unused center correction be preserved or corrected? | [interface audit](audits/openems-interfaces.md), [validation](VALIDATION.md) |

## Validation blockers

- The WSL root build, including Qt/VTK GUI compilation, Python, CTB, and the
  optional hyp2mat build, succeeded. CSXCAD C++ and Python tests, openEMS
  Python unit/simulation tests, Octave solver tests, both smoke tests, and the
  Sphinx build passed. See `VALIDATION.md` for exact results.
- No interactive GUI test, cross-platform build matrix, optional MPFR/GMP
  fparser build, or fixture-driven hyp2mat conversion was executed. Two capped
  MSL smoke runs and a compact analytic dipole reference are now preserved;
  repeated HDF5 and numeric probe outputs matched bitwise. The dipole case
  stops at its timestep cap. The conducting-sheet reference converges on all
  four runs, and repeated numeric traces match bitwise; five test repetitions
  recorded 20 solver-time samples and peak RSS. A 0.20 mm mesh sensitivity
  variant passed, while a coarser aligned 0.50 mm variant exceeded the
  resistive-film phase bound. Two repeats of the 3D Coax analytic test also
  converged at 2,264 timesteps, passed return-loss/transmission/impedance
  assertions, and matched saved port arrays bitwise. Solver timing is
  characterization only. More workload diversity and approved Rust
  comparison tolerances remain open.
- Several component questions remain unresolved by design (see the tables
  above). The source audits account for the tracked component families and
  cross-check public interface declarations; remaining compatibility and
  runtime gaps are explicit design/implementation risks rather than assumed
  behavior.

## Scope still open

The coverage matrix groups implementation files by component/path family;
detailed source and interface inventories are in the component audits.
Declaration checks confirm every CSXCAD/openEMS M-file function and every
public-named Cython method is represented. Residual gaps are focused runtime
validation, unresolved compatibility questions, cross-platform behavior, and
TODO/FIXME leads that were sampled but not adjudicated.
