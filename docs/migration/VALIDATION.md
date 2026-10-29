# Scientific and Compatibility Validation

## Current evidence

An original-stack baseline was built and exercised in Ubuntu 26.04.1 under
WSL on 2026-10-16. The root build succeeded with the GUI, Python bindings,
and CTB enabled; the optional hyp2mat build also succeeded. The native,
Python, Octave, smoke, and documentation test results are recorded below.
This is a headless single-platform baseline, not a completed migration
acceptance baseline: GUI interaction, cross-platform runs, optional fparser
backends, comprehensive immutable solver datasets, and performance/memory
characterization across representative workloads remain open.

### Original-stack WSL baseline

The isolated Linux checkout used the exact source revisions listed in
`MIGRATION_STATUS.md`. Toolchain: GCC/G++ 15.2.0, CMake 4.2.3, Python 3.14.4,
Octave 11.1.0, HDF5 1.14.6, TinyXML 2.6.2, Boost 1.90, CGAL 6.1.1, VTK
9.5.2, and Qt 6.10.2. The WSL host exposed a 13th Gen Intel Core i9-13900H
with 20 logical CPUs. The install prefix was
`/home/mberkanbicer/opt/openEMS`.

The initial offline `--python-venv-mode=site` build failed in Python metadata
preparation: `scripts/build_python.sh` appends `--system-site-packages` to
`pip_opt` instead of `pip_opts`, so the generated venv could not import the
system-installed `setuptools`. No source was changed. A manually created
system-site venv and `--python-venv-mode=disable --python-use-network=disable`
allowed the documented root build to complete without build isolation or
network access:

```sh
./update_openEMS.sh /home/mberkanbicer/opt/openEMS \
  --python --python-venv-mode=disable --python-use-network=disable \
  --with-CTB --njobs=4
./update_openEMS.sh /home/mberkanbicer/opt/openEMS \
  --with-hyp2mat --njobs=4
```

| Validation | Result |
| --- | --- |
| Root build with GUI, Python, and CTB | Passed |
| Optional hyp2mat root build and `hyp2mat --help` | Passed |
| CSXCAD C++ tests (`CSXCAD_BUILD_TESTS=ON`) | 2 passed |
| CSXCAD Python `unittest` suite | 150 passed, 1 skipped; targeted wrapper-cache tests 7/7 passed |
| openEMS Python unit suite | 10 passed |
| openEMS Python unit + simulation suite | 31 passed |
| openEMS Octave/Matlab suite | 10 passed |
| Octave and Python `MSL_NotchFilter` smoke tests | Passed |
| Sphinx HTML documentation build | Passed, 0 warnings |

Two cleanup-disabled Python MSL smoke runs produced immutable time-domain
field/port traces and HDF5 E/H spatial snapshots in
`reference-data/msl-notchfilter-wsl/`; the pinned input script hash, toolchain,
dataset hashes, and exact dump configuration are recorded there. All 12
numeric output arrays and all E/H HDF5 dataset arrays/attributes matched
exactly across repeated runs. Five solver-time measurements for the
269,780-cell, 1,000-step case ranged from 1.97494 s to 2.02864 s (median
1.99594 s, coefficient of variation 1.11%). The simulation reached its
1,000-step cap before the -60 dB termination criterion, so these outputs and
timings are repeatability evidence for a smoke case, not a converged physical
reference or cross-machine performance threshold.

The analytic references were run from the pinned repository root in the
configured WSL Python environment:

```sh
python3 openEMS/python/Tests/FieldProbes.py
python3 openEMS/python/Tests/Conducting_Sheet.py
```

For the retained raw captures, each script was executed without source edits
using a unique simulation output path and an in-memory `cleanup=False` override.
The compact artifacts, pinned input hashes, test assertions, comparison
results, and output checksums are documented in the following sections and
their reference-directory READMEs.

The pinned `openEMS/python/Tests/FieldProbes.py` analytic dipole case passed
eight runs in the same WSL environment. All runs passed the script's
probe/dump consistency, free-space D/E and B/H, frequency-domain, symmetry,
Hertzian-dipole, and VTK assertions. The first output set is checksummed under
`reference-data/fieldprobes-wsl/`; it retains the complete E/H time-domain
plane dumps, E/H frequency-domain dumps, and numeric probe traces. A compact
lossless keyframe file retains the quarter-run E/D/H/B fields and mesh/time
coordinates. The complete first output set contained 54 files (119 MiB); the
selected archive is 18,378,309 bytes. Repeat runs matched all 9 HDF5 files and
22 numeric text files bitwise, although only the compact subset and the first
run's full output checksums are retained.

The case used a 41x41x41 mesh (68,921 cells), 10,000 maximum timesteps, a
500 MHz frequency-domain probe, and 23 VTK slices. It did not reach its
-60 dB end criterion before the timestep cap, so it is an analytic
consistency/repeatability case, not a converged scientific acceptance case.
Observed relative differences were `D - eps0*E = 6.29e-9`,
`B - mue0*H = 5.30e-8`, and non-interpolated `B - mue0*H = 3.05e-8`;
the analytic E and H dipole-ratio errors were 5.07% and 4.18%, respectively.
The script's pass limits and its source SHA-256 are recorded with the
artifacts. Three cleanup-enabled repeats reported solver times of
9.61, 8.60, and 8.63 s (median 8.63 s, mean 8.94667 s, sample standard
deviation 0.5747 s, coefficient of variation 6.42%). These timings are
preliminary, exclude post-processing and cleanup, and do not satisfy the
planned converged-case performance or memory study.
Three additional process-isolated runs also passed; `/usr/bin/time` measured
peak resident memory at 121,788, 122,248, and 122,920 KiB (median 122,248
KiB), with end-to-end elapsed times of 11.73, 11.50, and 11.25 s. These
include Python startup, post-processing, and cleanup. They characterize only
this capped analytic case and do not supply a converged-case memory baseline.

The pinned `openEMS/python/Tests/Conducting_Sheet.py` analytic transmission
test supplies a converged scientific reference. The four 1D channel runs
(5,409 cells at 0.25 mm axial spacing) all reached the configured -50 dB
end-criteria at 1,460 steps for the empty reference and 1,314 steps for each
sheet case. Five separate full test runs passed; all 20 solver calls reached
the same scheduled stopping steps. The first run's four numeric probe traces
and per-frequency complex transmission results are preserved under
`reference-data/conducting-sheet-wsl/`; two cleanup-disabled captures matched
bitwise in all numeric trace rows and derived complex responses.

Across the 91 points from 1 to 10 GHz, the resistive-film case had maximum
analytic errors of 0.017 dB and 6.54 degrees, thin copper 0.099 dB and
3.84 degrees, and thick copper 1.982 dB; the measured thick-copper slope was
8.8 dB/decade against 10 analytically. Five process-isolated runs produced 20
solver-time observations from 0.027302 to 0.042648 s (median 0.029648 s, mean
0.031390 s, sample standard deviation 0.004501 s, coefficient of variation
14.34%). Per-process peak RSS ranged from 86,608 to 86,928 KiB (median 86,696
KiB); end-to-end wall time ranged from 0.38 to 0.72 s. The small workload and
timing variability make these platform-specific characterization data, not a
performance threshold.

For Rust acceptance, candidate analytic bounds are the source test's existing
limits: cases 1 and 2 require maximum magnitude error below 0.25 dB and phase
error below 10 degrees; case 3 requires magnitude error below 2.5 dB and a
10 +/- 2 dB/decade magnitude slope. At 0.20 mm axial spacing, the maximum
response change from the 0.25 mm reference was 0.0153 dB and 1.614 degrees
across these cases, and all source assertions passed. A 0.50 mm aligned grid
converged but exceeded the resistive-film phase limit at 12.39 degrees. A
0.30 mm grid did not align source/sheet/probe planes, produced an unused-source
warning and failed to converge; that run is invalid as a sensitivity sample.
These criteria are provisional analytic acceptance bounds, not approved
same-grid raw-field tolerances; the final comparison policy remains subject
to Task 15 review.

The pinned `openEMS/python/Tests/Coax.py` case adds a converged 3D reference.
It models a 150 mm air-filled coaxial line with a 97x97x76 mesh (715,084
cells), 0.25 mm transverse spacing, 2 mm axial spacing, and a 1-3 GHz,
201-point port sweep. Two runs reached the configured `EndCriteria=1e-4`
after 2,264 timesteps at -51.31 dB. Both passed the source assertions for
return loss, transmission, and analytic characteristic impedance; the maximum
impedance error was 1.20% against 49.939974651068 ohms. The maximum S11 was
-50.8824 dB and S21 ranged from -0.0081 to +0.0034 dB. All saved frequency,
port, and S-parameter arrays matched bitwise; all ten numeric rows in each
port text file matched after ignoring timestamp headers, and the E/H HDF5
files had matching hashes. Solver times were 11.33 and 12.03 seconds; these
two observations characterize this WSL run only and are not a performance
threshold. Compact arrays, solver outputs, and reproduction metadata are in
`reference-data/coax-3d-wsl/`.
The source assertions can be rerun from the repository root with:

```bash
source /home/mberkanbicer/python-venv-verified/bin/activate
python3 openEMS/python/Tests/Coax.py
```

The retained runs executed the same pinned source without editing it, redirecting
each output path and disabling cleanup in memory so solver outputs and port
arrays could be captured.

The original fparser CMake target built on Windows with Visual Studio
2022/MSVC 19.44. Its example evaluated `x^2` at -1, 0, and 1 as 1, 0, and 1.
A separate build enabling float, long double, and long integer ran the second
example: double and float produced visibly different precision, Windows long
double matched double, and integer `x*x` produced 0, 1, 4 for inputs 0, 1, 2.
Two more default-double probes returned `sin(0) = 0`, `sin(1.5) = 0.997495`,
`sin(3) = 0.14112`, and true (`1`) for a constant sum of ten `0.1` terms
compared with 1. A temporary C++ probe linked against the original parser
sources and observed error codes 1-4, stale error state after an invalid parse,
inline-variable result 27 for `a:=x*x; a+2*a` at `x=3`, correct skipping of an
erroring unselected `if` branch, and child-parser error propagation.
Optimization also removed an observable callback from `0*count(x)` and
`0&count(x)`. A separate complex-double build returned approximately
`6.12323e-17 - i` for `sqrt(-1)` and `sqrt(0-1)`; for `sqrt(x)`, the imaginary
sign followed the sign of zero in the input (`x=(-1,+0)` returned `+i`,
`x=(-1,-0)` returned `-i`). Optimizing `sqrt(-1)` preserved that result.
A separate build enabled all three complex scalar types and evaluated
`sqrt(-1)`: double and long double returned approximately
`6.12323e-17 - i`, while float returned approximately `-4.37114e-08 - i`.
Further default-double probes returned `7` for `1+2*3`, `-4` for `-2^2`,
`1`/`0` for equality at/just beyond the `1e-12` absolute epsilon,
`0`/`1` for corresponding less-than boundary checks, and `0`/`1` for logical
truth inputs `0.4999`/`0.5`. With `cm=0.01`, `5/2cm` returned `250` while
`(5/2)cm` returned `0.025`; `sin(90)` parsed in degree mode returned `1`.
The optimized/unoptimized expression sample matched values and errors for
trigonometric identity, conditional square roots, `log(exp(x))`, a quadratic,
and `x^0` at `x=-2,0,2`. It did not preserve the error from `0*log(-2)`:
unoptimized evaluation reported error 3, while optimized evaluation returned
zero with no error. `x/x` at zero already evaluated to 1 before explicit
optimization, indicating a compile-time rewrite.
These are component behavior probes only, not comprehensive parser or
numerical-boundary validation. The build under `%TEMP%` emitted MSBuild path
warnings; compiling the example emitted narrowing-conversion warnings from
generated optimizer code. MPFR and GMP variants and other platform builds were
not exercised in that initial baseline. Their headers were unavailable at the
checked MSYS2 and vcpkg locations, and no dependency was installed. A later WSL
check found MPFR 4.2.2 and GMP 6.3.0 already installed. Separate C++98 builds
of `fparser.cc`, `fpoptimizer.cc`, and the corresponding wrapper sources
succeeded; arithmetic probes returned `1.01` for MPFR `x*x+1` at `x=0.1` and
the exact GMP integer `15241578750190522` for `x*x+1` at `x=123456789`. The
MPFR build emitted a deprecation warning for `mpfr_root`. No dependency was
installed. Broader backend compatibility and installation packaging remain
unverified. Temporary probe source and build outputs were removed after
recording their results. A separate focused probe exercised every source-listed
built-in in the default double parser: all real-valued functions evaluated
without errors, while the five complex-only names failed with
`UNKNOWN_IDENTIFIER`. A complex-double build then evaluated all five
complex-only functions without errors. Exact outputs are in
`audits/fparser.md`. These probes do not cover all domains, variants, or
optimizer transformations.

## Additional component evidence

- **CTB:** MATLAB R2025b exercised representative transform singularities,
  zero/negative reference impedances, matrix shape errors, malformed and
  truncated Touchstone records, zero/negative frequencies, and network
  operation edge cases. Hz/kHz/MHz/GHz scaling and RI/MA/DB decoding also
  matched their sample expectations. An invalid-unit exception left the input
  file open, confirmed with `openedFiles`. The complete observed outputs and
  unresolved cross-product gaps are in `audits/ctb.md`.

  A separate three-frequency, two-port transform probe used asymmetric
  reference impedances `[50;75]`; `s2y`/`y2s`, `s2z`/`y2z`, `s2z`/`z2y`, and
  `s2a`/`a2s` round trips all passed with maximum absolute error below
  `4.3e-14`:

  ```powershell
  matlab -batch "addpath('CTB'); S=zeros(2,2,3); for k=1:3, S(:,:,k)=[0.1+0.01i*k,0.2-0.02i*k;0.7+0.03i*k,-0.1+0.01i*k]; end; Z=s2z(S,[50;75]); Y=s2y(S,[50;75]); S2=y2s(Y,[50;75]); Z2=y2z(Y); Y2=z2y(Z); A=s2a(S,50); S3=a2s(A,50); e1=max(abs(S(:)-S2(:))); e2=max(abs(Z(:)-Z2(:))); e3=max(abs(Y(:)-Y2(:))); e4=max(abs(S(:)-S3(:))); assert(max([e1,e2,e3,e4])<1e-12); fprintf('CTB transform round-trips passed; max errors %.3g %.3g %.3g %.3g\n',e1,e2,e3,e4);"
  ```

  A 3-port S/Z/Y round trip with distinct references also passed at all three
  frequency slices; maximum absolute errors were `1.25e-16` (S/Z) and
  `7.08e-17` (S/Y):

  ```powershell
  matlab -batch "addpath('CTB'); S=zeros(3,3,3); for k=1:3, S(:,:,k)=[0.10+0.01i*k,0.02-0.01i*k,0.03;0.04,0.08+0.01i*k,0.02;0.01,0.05,0.12-0.02i*k]; end; ref=[50;75;60]; Z=s2z(S,ref); Y=s2y(S,ref); Sz=z2s(Z,ref); Sy=y2s(Y,ref); ez=max(abs(S(:)-Sz(:))); ey=max(abs(S(:)-Sy(:))); assert(max(ez,ey)<1e-12); fprintf('CTB 3-port transform round-trips passed; max errors %.3g %.3g\n',ez,ey);"
  ```

  Two-frequency, two-port Touchstone S/Z/Y files also round-tripped through
  the writer and reader exactly; omitted references were `50` for S and `1`
  for Z/Y:

  ```powershell
  matlab -batch "addpath('CTB'); freq=[1e6 2e6]; D=zeros(2,2,2); D(:,:,1)=[0.1+0.02i,0.3-0.01i;0.7+0.05i,-0.2+0.03i]; D(:,:,2)=[-0.1+0.01i,0.2+0.02i;0.6-0.04i,0.15+0.03i]; types={'s','z','y'}; errs=zeros(1,3); for k=1:3, f=[tempname,'.s2p']; try, write_touchstone(types{k},freq,D,f); [t,fr,R,ref]=read_touchstone(f); errs(k)=max(abs(D(:)-R(:))); wantref=1; if types{k}=='s', wantref=50; end; assert(t==types{k} && max(abs(fr-freq))<1e-9 && ref==wantref && errs(k)<1e-5); delete(f); catch e, if exist(f,'file'), delete(f); end; rethrow(e); end; end; fprintf('CTB 2-port Touchstone S/Z/Y round trips passed; max errors %.3g %.3g %.3g\n',errs);"
  ```

  Renormalization between distinct per-port reference vectors and back passed
  for a three-port, two-frequency S matrix:

  ```powershell
  matlab -batch "addpath('CTB'); S=zeros(3,3,2); for k=1:2, S(:,:,k)=[0.1+0.01i*k,0.02,0.03;0.04,0.08-0.01i*k,0.02;0.01,0.05,0.12+0.02i*k]; end; old=[50;75;60]; new=[75;60;50]; Snew=s_renorm(S,old,new); Sback=s_renorm(Snew,new,old); err=max(abs(S(:)-Sback(:))); assert(err<1e-12); fprintf('CTB unequal-reference 3-port renormalization round trip passed; max error %.3g\n',err);"
  ```

  `s2z` and `s2y` were also compared with independently assembled direct
  equations for a three-port S matrix and `[50;75;60]` ohm references:

  ```powershell
  matlab -batch "addpath('CTB'); S=zeros(3,3,3); for k=1:3, S(:,:,k)=[0.10+0.01i*k,0.02-0.01i*k,0.03;0.04,0.08+0.01i*k,0.02;0.01,0.05,0.12-0.02i*k]; end; ref=[50;75;60]; Rroot=diag(sqrt(ref)); Rinv=diag(1./sqrt(ref)); Ze=zeros(size(S)); Ye=zeros(size(S)); I=eye(3); for k=1:3, Ze(:,:,k)=Rroot*((I-S(:,:,k))\(I+S(:,:,k)))*Rroot; Ye(:,:,k)=Rinv*((I+S(:,:,k))\(I-S(:,:,k)))*Rinv; end; Z=s2z(S,ref); Y=s2y(S,ref); ez=max(abs(Z(:)-Ze(:))); ey=max(abs(Y(:)-Ye(:))); assert(max(ez,ey)<1e-12); fprintf('CTB 3-port S-to-Z/Y analytic equations passed; max errors %.3g %.3g\n',ez,ey);"
  ```
  The renormalized 3-port S matrix also preserved its Z matrix across
  `[50;75;60]` to `[75;60;50]` reference conversion:

  ```powershell
  matlab -batch "addpath('CTB'); S=zeros(3,3,2); for k=1:2, S(:,:,k)=[0.1+0.01i*k,0.02,0.03;0.04,0.08-0.01i*k,0.02;0.01,0.05,0.12+0.02i*k]; end; old=[50;75;60]; new=[75;60;50]; Snew=s_renorm(S,old,new); Zold=s2z(S,old); Znew=s2z(Snew,new); err=max(abs(Zold(:)-Znew(:))); assert(err<1e-12); fprintf('CTB renormalization impedance invariant passed; max Z error %.3g\n',err);"
  ```

  The 2-port S/ABCD conversion also passed for a single-frequency array:

  ```powershell
  matlab -batch "addpath('CTB'); S=reshape([0.1+0.02i,0.3-0.01i;0.7+0.05i,-0.2+0.03i],2,2,1); A=s2a(S,50); S2=a2s(A,50); err=max(abs(S(:)-S2(:))); assert(err<1e-12); fprintf('CTB single-frequency S/ABCD round trip passed; max error %.3g\n',err);"
  ```
- **QCSXCAD/AppCSXCAD:** `cmake -S QCSXCAD -B <temporary-build-dir>` ran with
  MSVC 19.44 and failed during configure because the CSXCAD library/include
  paths and TinyXML library/include files were missing. Later, the complete
  WSL root build compiled QCSXCAD and AppCSXCAD and linked the Qt6/VTK runtime
  libraries. No interactive GUI test was possible in the headless session;
  exact source findings are in `audits/gui.md`.
- **CSXCAD Matlab/Octave:** MATLAB R2025b `struct_2_xml` probe with an `A&B`
  attribute, `A&B` text value, and empty numeric field passed assertions that
  the DOM output escaped ampersands and omitted the empty field. The temporary
  XML file was removed. Octave is now available; the separate writer was
  tested with the same input shape and confirmed to emit raw ampersands and an
  explicit empty element. A missing output directory caused `fprintf` to fail
  with `invalid stream number = -1` after `fopen` returned its unchecked error
  value. The probe assertions were:

  ```octave
  addpath('CSXCAD/matlab');
  f = [tempname(), '.xml'];
  s.ATTRIBUTE.Attr = 'A&B'; s.Text = 'A&B'; s.Empty = [];
  struct_2_xml(f, s, 'root'); out = fileread(f);
  assert(!isempty(strfind(out, 'Attr="A&B"')));
  assert(!isempty(strfind(out, '<Text>A&B</Text>')));
  assert(!isempty(strfind(out, '<Empty></Empty>'))); unlink(f);
  ```

  A second probe confirmed the unchecked `fopen` path reports the downstream
  Octave stream error:

  ```octave
  p = [tempname(), '/missing/subdir.xml']; failed = false;
  try
    struct_2_xml(p, struct(), 'root');
  catch err
    failed = true;
    assert(!isempty(strfind(err.message, 'invalid stream number = -1')));
  end
  assert(failed);
  ```
  A second MATLAB probe passed an unknown `AddProbe` option with numeric value
  `42`; the emitted warning used `"*"` rather than the option key because the
  warning formats the value argument. The call completed and `lastwarn`
  returned identifier `CSXCAD:AddProbe`.
  A `CheckMesh([0 2],0,1,1.3,...)` probe returned no error data with
  `be_quiet=1`, but returned one max-resolution error (position 1, type 1)
  with `be_quiet=0`; quiet mode suppresses results as well as warnings.
  Calling `Convert_VF_DiscMaterial` with an unknown option and nonexistent
  input paths failed immediately with `Undefined variable 'varagin'.`, before
  file access. The converter's full workflow remains unrun because the
  required Virtual Family/database inputs are unavailable.
- **openEMS and scripting interfaces:** The MATLAB pure-M-file unit groups
  passed 17 checks, as recorded in `audits/openems-core.md`. The later WSL
  baseline built the native solver and Python extensions. The Python full
  suite passed all 31 unit and simulation tests; the Octave suite passed all
  10 tests and compared all four engines' field dumps. Both language smoke
  tests passed. GUI interaction and cross-platform behavior remain untested.
  An earlier Python unit-runner attempt, before installing the documented
  dependencies, was:

  ```powershell
  python openEMS\python\Tests\run_testsuite.py --only-unittests --timeout=30
  ```

  It ran 10 tests: `test_sim_scripts.py` passed, while nine errored at import
  (eight missing NumPy, one missing `openEMS`). This was an initial
  environment-readiness failure and is superseded by the passing WSL baseline
  above.

  The MATLAB `transforms` group was also run directly. Its five Gaussian,
  DFT/FFT agreement, truncated-record, and periodic-sine checks passed; maximum
  relative deviations were `1.7e-15`, `3.57e-15`, `2.07e-15`, `3.2e-12`, and
  `1.23e-16`, respectively.
  The `harminv` executable was not on `PATH` and was absent from its expected
  Windows location, so that helper was not invoked end-to-end.

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); addpath('openEMS\matlab'); addpath('openEMS\TESTSUITE\unittests'); assert(transforms());"
  ```

  MATLAB R2025b HDF5 round-trip probes used `WriteHDF5` with temporary files.
  An FD-only field plus Cartesian mesh round-tripped values successfully
  through `ReadHDF5Dump`; frequency and mesh vectors were returned as columns,
  so the assertions compared normalized vector orientation. Adding TD samples
  failed in `ReadHDF5FieldData` with `Invalid field name: '1/time'.` The
  reader's `hdf5info` attribute name includes the dataset name, which its
  regular expression retains as part of the dynamic struct field name. Both
  temporary files were removed. These focused MATLAB probes do not replace
  the missing solver-backed HDF5 reference comparison.

  The TD failure was reproduced with:

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); addpath('openEMS\matlab'); f=[tempname,'.h5']; try, h.TD.time=[0 1]; h.TD.values={reshape(1:8,[2 2 2]),reshape(9:16,[2 2 2])}; h.FD.frequency=[1e6 2e6]; h.FD.values={complex(ones(2,2,2),2*ones(2,2,2)),complex(3*ones(2,2,2),4*ones(2,2,2))}; m.type=0; m.names={'/Mesh/x','/Mesh/y','/Mesh/z'}; m.lines={[0 1],[0 2],[0 3]}; WriteHDF5(f,h,m); [r,rm]=ReadHDF5Dump(f); delete(f); catch e, if exist(f,'file'), delete(f); end; rethrow(e); end"
  ```

  The FD/mesh value round-trip was reproduced with:

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); addpath('openEMS\matlab'); f=[tempname,'.h5']; try, h.FD.frequency=[1e6 2e6]; h.FD.values={complex(ones(2,2,2),2*ones(2,2,2)),complex(3*ones(2,2,2),4*ones(2,2,2))}; m.type=0; m.names={'/Mesh/x','/Mesh/y','/Mesh/z'}; m.lines={[0 1],[0 2],[0 3]}; WriteHDF5(f,h,m); [r,rm]=ReadHDF5Dump(f); assert(isequal(r.FD.frequency(:)',h.FD.frequency)); assert(isequal(r.FD.values{1},h.FD.values{1}) && isequal(r.FD.values{2},h.FD.values{2})); assert(all(cellfun(@(a,b) isequal(a(:)',b(:)'),rm.lines,m.lines))); delete(f); disp('MATLAB HDF5 FD/mesh value round-trip passed (vector orientation normalized)'); catch e, if exist(f,'file'), delete(f); end; rethrow(e); end"
  ```

  Spherical vector conversion was checked against the analytic radial unit
  vector at theta=phi=90 degrees:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); f=[tempname,'.vtk']; try, m.type=2; m.lines={[1],[pi/2],[pi/2]}; q=reshape([1 0 0],[1 1 1 3]); Dump2VTK(f,q,m,'E'); out=fileread(f); disp(out); delete(f); catch e, if exist(f,'file'), delete(f); end; rethrow(e); end"
  ```

  The source emitted approximately `(0,0,0)`; the expected Cartesian vector is
  `(0,1,0)`. No M-file was changed; this is recorded as a compatibility finding
  pending migration behavior decisions.

  Pure field-processing helpers were exercised with a scalar field
  `x + 2*y + 3*z + t` on a 3x2x2 Cartesian mesh and three uniformly spaced
  time samples. Range selection, `[2 1 2]` subsampling, interpolation onto five
  X coordinates, and the zero-frequency TD-to-FD sum all passed assertions.
  A separate probe requested scalar X range `2` on mesh `[0 1]`; MATLAB
  reproduced `Index exceeds the number of array elements` from the one-value
  fallback. The analytic field test was run as:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); m.type=0; m.lines={[0 1 2],[0 1],[0 1]}; [X,Y,Z]=ndgrid(m.lines{1},m.lines{2},m.lines{3}); f.TD.time=[0 .5 1]; for k=1:3, f.TD.values{k}=X+2*Y+3*Z+f.TD.time(k); end; f.TD.names={'1','2','3'}; [r,mr]=GetField_Range(f,m,{[1 2],[0],[]}); assert(isequal(mr.lines{1},[1 2]) && isequal(mr.lines{2},0) && isequal(size(r.TD.values{1}),[2 1 2])); [s,ms]=GetField_SubSampling(f,m,[2 1 2]); assert(isequal(ms.lines{1},[0 2]) && isequal(ms.lines{3},0) && isequal(s.TD.values{2},f.TD.values{2}([1 3],:,1,:))); li={linspace(0,2,5),[],[]}; [i,mi]=GetField_Interpolation(f,m,li); [Xi,Yi,Zi]=ndgrid(mi.lines{1},mi.lines{2},mi.lines{3}); expected=Xi+2*Yi+3*Zi+f.TD.time(2); assert(max(abs(i.TD.values{2}(:)-expected(:)))<1e-12); g=GetField_TD2FD(f,0); expectedFD=2*.5*(f.TD.values{1}+f.TD.values{2}+f.TD.values{3}); assert(isequal(g.FD.frequency,0) && max(abs(g.FD.values{1}(:)-expectedFD(:)))<1e-12); disp('MATLAB field range/subsampling/interpolation/TD2FD probes passed');"
  ```

  The scalar out-of-range failure was reproduced with:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); m.lines={[0 1],[0],[0]}; caught=false; try, GetField_Range([],m,{2,[],[]}); catch e, caught=contains(e.message,'Index exceeds'); disp(e.message); end; assert(caught); disp('MATLAB scalar out-of-range probe reproduced the range-index error');"
  ```

  `calcWGPort` reference-plane handling was exercised with minimal U/I probe
  text files. The branch failed at `real(beta)` because MATLAB resolved bare
  `beta` to its built-in function:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); d=tempname; mkdir(d); try, U=[0 1;1e-12 .5;2e-12 0;3e-12 -.5]; I=U; dlmwrite(fullfile(d,'U.txt'),U,'delimiter',' '); dlmwrite(fullfile(d,'I.txt'),I,'delimiter',' '); p.type='WaveGuide'; p.U_filename='U.txt'; p.I_filename='I.txt'; p.kc=1; p.drawingunit=1; p.measplanepos=0; try, calcWGPort(p,d,[1e9 2e9],'RefPlaneShift',1); catch e, disp(getReport(e,'extended')); end; delete(fullfile(d,'U.txt')); delete(fullfile(d,'I.txt')); rmdir(d); catch e, if exist(fullfile(d,'U.txt'),'file'), delete(fullfile(d,'U.txt')); end; if exist(fullfile(d,'I.txt'),'file'), delete(fullfile(d,'I.txt')); end; if exist(d,'dir'), rmdir(d); end; rethrow(e); end"
  ```

  The legacy MSL excitation option was probed with an initialized Cartesian
  mesh and metal. Although the supplied string was empty, `port.excite` was 1:

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); addpath('openEMS\matlab'); c=InitCSX(); m.x=[0 1 2 3 4]; m.y=[-1 -.5 0 .5 1]; m.z=[-3 -2 -1 0 1 2]; c=DefineRectGrid(c,1,m); c=AddMetal(c,'metal'); [c,p]=AddMSLPort(c,1,1,'metal',[0 -.5 0],[4 .5 -1],'x',[0 0 -1],'ExcitePort',''); disp(p.excite); assert(p.excite==1); disp('MATLAB empty legacy ExcitePort string enabled the MSL excitation');"
  ```

  The deprecated NF2FF function's documented optional radius was checked by
  calling it with the five non-radius arguments; the implementation failed at
  its exact-six-argument check:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); caught=false; try, AnalyzeNF2FF('unused',struct(),1,[0],[0]); catch e, caught=contains(e.message,'Not enough input'); disp(e.message); end; assert(caught); disp('MATLAB AnalyzeNF2FF radius documented optional but required');"
  ```

  The CSXCAD MATLAB writer edge probe was run as:

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); q=struct(); q.ATTRIBUTE.note='A&B'; q.text='A&B'; q.empty=[]; f=[tempname,'.xml']; struct_2_xml(f,q,'Root'); out=fileread(f); assert(contains(out,'A&amp;B')); assert(~contains(out,'<empty')); delete(f)"
  ```

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); c=InitCSX(); lastwarn(''); c=AddProbe(c,'p',0,'Bogus',42); [msg,id]=lastwarn; assert(strcmp(id,'CSXCAD:AddProbe')); assert(contains(msg,'*')); disp(msg)"
  ```

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); [eQuiet,pQuiet,tQuiet]=CheckMesh([0 2],0,1,1.3,1); [eReport,pReport,tReport]=CheckMesh([0 2],0,1,1.3,0); assert(eQuiet==0 && isempty(pQuiet) && isempty(tQuiet)); assert(eReport==1 && isequal(pReport,1) && isequal(tReport,1))"
  ```

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); caught=false; try, Convert_VF_DiscMaterial('missing','missing.h5','unused.h5','Bogus',1); catch e, caught=contains(e.message,'varagin'); disp(e.message); end; assert(caught)"
  ```

  MATLAB R2025b also resolved a bundled phantom through
  `openEMS_resource_path` after changing the working directory to `tempdir`;
  a missing resource raised `openEMS:resource_not_found`. This confirms the
  helper's function-relative behavior but does not validate installed layouts.

  ```powershell
  matlab -batch "orig=pwd; addpath(fullfile(orig,'openEMS','matlab')); cd(tempdir); p=openEMS_resource_path('phantoms','phantom_head_298MHz.h5'); assert(isfile(p)); try, openEMS_resource_path('__missing_resource__'); error('probe:expectedFailure'); catch e, assert(strcmp(e.identifier,'openEMS:resource_not_found')); end; disp('MATLAB resource lookup found packaged phantom from a changed working directory and raised the documented error identifier for a missing resource');"
  ```

  MATLAB R2025b also exercised `AR_estimate` on a constant signal and its
  error-code paths for mismatched lengths, `mu <= 2*nu`, `expand_factor <= 1`,
  and too-short input; constant extrapolation and codes `1`, `2`, `3`, and
  `10` passed:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); t=0:9; v=ones(1,10); [va,ta,fa,e0]=AR_estimate(t,v,0,1,4,2); assert(e0==0 && numel(va)==20 && numel(ta)==20 && numel(fa)==1); [~,~,~,e1]=AR_estimate(t,v(1:9),0,1,4,2); [~,~,~,e2]=AR_estimate(t,v,0,1,2,2); [~,~,~,e3]=AR_estimate(t,v,0,1,4,1); [~,~,~,e10]=AR_estimate(0:4,ones(1,5),0,1,10,2); assert(isequal([e1 e2 e3 e10],[1 2 3 10])); disp('MATLAB AR_estimate valid extrapolation and error-code probes passed');"
  ```

  A synthetic MATLAB mesh verified `AddPML`'s per-face cell extension and that
  zero counts leave the mesh unchanged:

  ```powershell
  matlab -batch "addpath('openEMS\matlab'); m.x=[0 1 3]; m.y=[0 2 5]; m.z=[0 4]; q=AddPML(m,[1 2 0 1 1 1]); assert(isequal(q.x,[-1 0 1 3 5 7]) && isequal(q.y,[0 2 5 8]) && isequal(q.z,[-4 0 4 8])); q2=AddPML(m,0); assert(isequal(q2,m)); disp('MATLAB AddPML directional padding and zero-padding probes passed');"
  ```

  A MATLAB R2025b probe of the exact `vectorEqual` comparison expression
  reproduced an incorrect equality for distinct vectors: `[1;1]` and `[2;0]`
  yield per-column mismatch flags `[true false]`, which do not enter the
  helper's vector `if` branch.

  ```powershell
  matlab -batch "v1=[1;1]; v2=[2;0]; acc=1e-6; mismatch=sum(abs((v1(:)-v2(:))/v1(:))>acc)>0; if mismatch, equal=0; else, equal=1; end; assert(equal==1 && any(v1~=v2)); disp('MATLAB right-division expression accepted distinct comparison vectors');"
  ```

  Source inspection mapped `invoke_openEMS`, `setup`, and the Octave-only
  `ensure_oct_file` recovery path. The Octave suite later passed in WSL, but
  the solver-launcher error paths and forced oct-file rebuild/recovery path
  were not directly exercised; directory-restoration and platform-specific
  logging behaviors remain source observations, not runtime results.
  Further source review mapped `DumpFF2VTK`, MATLAB/Octave HDF5 field and mesh
  readers, attribute access, and waveguide mode-file serialization. No direct
  helper tests were found for most paths; a focused Octave mesh fixture probe
  is recorded below, while the Octave field reader and mode-file writer remain
  without direct fixture coverage.
  A MATLAB R2025b focused mode-file probe passed for coordinates, component
  matrices as exposed by `h5read`, and the root `Version` attribute:

  ```powershell
  matlab -batch "addpath('CSXCAD\matlab'); addpath('openEMS\matlab'); f=[tempname '.h5']; c=onCleanup(@() delete(f)); x=[1 2]; y=[10 20 30]; Vx=reshape(1:6,2,3); Vy=10*Vx; h5writemode(f,x,y,Vx,Vy); xf=h5read(f,'/x'); yf=h5read(f,'/y'); vxf=h5read(f,'/Vx'); vyf=h5read(f,'/Vy'); assert(isequal(xf(:)',x)); assert(isequal(yf(:)',y)); assert(isequal(vxf,Vx.')); assert(isequal(vyf,Vy.')); assert(h5readatt(f,'/','Version')==1); disp('MATLAB h5writemode coordinates, transposed components, and Version attribute passed');"
  ```
  Source-only contracts were also added for optimizer callbacks and cache
  naming, the four-run directional-coupler example and its local Y-to-S
  conversion, CRLH geometry hints, and patch-array setup. The solver-backed
  examples and direct tests were not run.

- **openEMS Python port post-processing:** A synthetic WSL probe using the
  verified system-site Python environment exercised `_load_ui_file` header
  parsing and invalid-header rejection, `Port.ReadUIData` time-series
  summation, `Port.CalcPort` incident/reflected wave identities, and incident
  power calculation. All assertions passed. This checks the Python-level
  contract only; no solver-produced files, mismatched probe time axes, or
  reference-plane shifts were involved.

  Reproduce from the repository root in the WSL baseline:

  ```bash
  source /home/mberkanbicer/python-venv-verified/bin/activate
  python3 - <<'PY'
  import os
  import tempfile
  import numpy as np
  from openEMS.ports import Port, _load_ui_file

  with tempfile.TemporaryDirectory() as directory:
      header = os.path.join(directory, "header.txt")
      with open(header, "w", encoding="utf-8") as stream:
          stream.write("% t/s voltage mode_purity\n0 2 0.25\n1e-9 4 0.5\n")
      data, columns = _load_ui_file(header)
      assert data.shape == (2, 3) and columns == ["t/s", "voltage", "mode_purity"]
      assert np.array_equal(data[:, 1], [2.0, 4.0])

      invalid = os.path.join(directory, "invalid-header.txt")
      with open(invalid, "w", encoding="utf-8") as stream:
          stream.write("% time voltage\n0 2\n")
      try:
          _load_ui_file(invalid)
      except ValueError:
          pass
      else:
          raise AssertionError("invalid first column was accepted")

      times = [0, 1e-9, 2e-9, 3e-9]
      for name, values in (("u.txt", [2, 2, 2, 2]), ("i.txt", [1, 1, 1, 1])):
          with open(os.path.join(directory, name), "w", encoding="utf-8") as stream:
              stream.write("% t/s value\n")
              stream.writelines(f"{t} {v}\n" for t, v in zip(times, values))
      port = Port(None, 1, [0, 0, 0], [1, 1, 1], 0,
                  U_filenames=["u.txt"], I_filenames=["i.txt"])
      port.CalcPort(directory, [0.0], ref_impedance=2)
      assert np.array_equal(port.ut_tot, [2, 2, 2, 2])
      assert np.array_equal(port.it_tot, [1, 1, 1, 1])
      assert np.allclose(port.uf_inc + port.uf_ref, port.uf_tot)
      assert np.allclose(port.if_inc - port.if_ref, port.if_tot)
      assert np.allclose(port.P_inc, 0.5 * np.real(port.uf_inc * np.conj(port.if_inc)))
      assert port.u_mode_purity == [None]
  PY
  ```

- **openEMS simulation-path cleanup:** A WSL Octave probe created a temporary
  directory containing whitelisted solver outputs, an unrelated text file,
  and an unreadable `.h5` file. `CleanupSimPath` removed the known outputs,
  preserved both unrelated files, and created a requested missing directory;
  all assertions passed. The probe did not create a genuine openEMS HDF5 dump,
  so fingerprint-based HDF5 deletion remains untested.

  ```bash
  octave --no-gui --quiet --eval "addpath('openEMS/matlab'); root=tempname(); mkdir(root); unwind_protect; names={'et','ht','port_ut1','port_it1','mesh.vtk','notes.txt','unrelated.h5'}; for k=1:numel(names), fid=fopen(fullfile(root,names{k}),'w'); assert(fid>=0); fprintf(fid,'keep or delete'); fclose(fid); end; CleanupSimPath(root,0); assert(~exist(fullfile(root,'et'),'file')); assert(~exist(fullfile(root,'ht'),'file')); assert(~exist(fullfile(root,'port_ut1'),'file')); assert(~exist(fullfile(root,'port_it1'),'file')); assert(~exist(fullfile(root,'mesh.vtk'),'file')); assert(exist(fullfile(root,'notes.txt'),'file')==2); assert(exist(fullfile(root,'unrelated.h5'),'file')==2); missing=fullfile(root,'created'); CleanupSimPath(missing,0); assert(exist(missing,'dir')==7); unwind_protect_cleanup; if exist(root,'dir'), rmdir(root,'s'); end; end_unwind_protect; disp('CleanupSimPath whitelist, unrelated-file preservation, and directory creation passed');"
  ```

- **openEMS Octave HDF5 mesh reader:** Synthetic Cartesian, cylindrical, and
  spherical HDF5 fixtures passed the type and line-array ordering checks. The
  cylindrical result exposes a confirmed label/value mismatch: `lines` are
  returned in rho/alpha/z order, while `names` remain alpha/rho/z; Cartesian
  and spherical names match their line arrays. The cause is the Octave
  `fieldnames` column vector being passed through `fliplr` (no-op), while the
  line cell array is row-shaped and does reverse. No submodule source was
  changed.

  Reproduce in the WSL baseline from the repository root:

  ```bash
  source /home/mberkanbicer/python-venv-verified/bin/activate
  python3 - <<'PY'
  import os
  import subprocess
  import tempfile
  import h5py
  import numpy as np

  cases = {
      "cartesian": [("x", [0, 1]), ("y", [2, 3, 4]), ("z", [5, 6, 7, 8])],
      "cylindrical": [("alpha", [0, 1]), ("rho", [2, 3, 4]), ("z", [5, 6, 7, 8])],
      "spherical": [("phi", [0, 1]), ("r", [2, 3, 4]), ("theta", [5, 6, 7, 8])],
  }
  expected = {
      "cartesian": (0, ["x", "y", "z"], [2, 3, 4]),
      "cylindrical": (1, ["alpha", "rho", "z"], [3, 2, 4]),
      "spherical": (2, ["r", "theta", "phi"], [3, 4, 2]),
  }
  with tempfile.TemporaryDirectory() as directory:
      code = ["addpath('openEMS/matlab');"]
      for name, axes in cases.items():
          path = os.path.join(directory, name + ".h5")
          with h5py.File(path, "w") as output:
              mesh = output.create_group("Mesh")
              for axis, values in axes:
                  mesh.create_dataset(axis, data=np.asarray(values, dtype=np.float64))
          path = path.replace("'", "''")
          mesh_type, labels, lengths = expected[name]
          code.extend([
              f"m=ReadHDF5Mesh('{path}');",
              f"assert(m.type=={mesh_type});",
              *[f"assert(strcmp(m.names{{{index}}},'/Mesh/{label}'));" for index, label in enumerate(labels, 1)],
              f"assert(isequal(cellfun(@numel,m.lines),[{ ' '.join(map(str, lengths)) }]));",
              f"fprintf('{name} type=%d names=',m.type); disp(m.names');",
              "fprintf('line counts='); disp(cellfun(@numel,m.lines));",
          ])
      subprocess.run(["octave", "--no-gui", "--quiet", "--eval", " ".join(code)], check=True)
  PY
  ```

## Reference environment readiness

The initial Windows audit environment lacked Octave and the native runtime.
The baseline was therefore captured in an isolated Ubuntu 26.04.1 WSL clone
created from local Git bundles because the Windows worktree's `.git` metadata
points to a drive unavailable inside WSL. Its root and seven submodule
checkouts match the pinned commits recorded in `MIGRATION_STATUS.md`. The
installed native libraries, Python bindings, and Octave interfaces imported
or executed from `/home/mberkanbicer/opt/openEMS`; no baseline source changes
were made. Build and test dependencies were installed in WSL only.

## Reference capture

For each Rust unit:

1. Record the exact root and submodule commits, operating system, compiler,
   build options, dependency versions, and runtime configuration.
2. Build the original component stack using the repository's documented build
   flow and retain build logs.
3. Run representative existing unit, integration, smoke, and end-to-end tests.
   Preserve their inputs and outputs as immutable reference artifacts.
4. For scientific cases, capture intermediate values at meaningful boundaries
   (input parsing, mesh/material setup, operator coefficients, time-step
   fields, and post-processing) where the original interfaces permit.
5. Add analytical or manufactured-solution references and physical invariants
   appropriate to each algorithm. Record the derivation and units.
6. Measure runtime and memory on declared hardware using repeatable workloads.

Do not edit or regenerate reference results to make a migrated implementation
pass.

## Comparison rules

- Compare identical input files, meshes, parameters, boundary conditions,
  precision, and solver settings.
- Use bitwise comparison only when operation order and runtime are intended to
  remain identical. Otherwise define case-specific absolute, relative, and
  norm-based tolerances from analytical error, original repeatability, and
  sensitivity evidence before evaluating the Rust result.
- Compare intermediate state as well as final output. Investigate every
  discrepancy beyond the predeclared criteria; do not mask it with broader
  tolerances.
- Check units, dimensions, coordinate conventions, conservation/physical
  constraints, convergence behavior, and deterministic behavior where
  applicable.
- Verify XML and other file-format round trips, existing-project loading,
  Python/Matlab APIs, GUI workflows, and cross-platform builds independently
  from numerical equivalence.
- Record command, environment, input/reference identifiers, comparison method,
  tolerances, result, and unresolved differences for every validation run.

## Existing validation entry points

These commands are documented by the project instructions and must be run in
an environment with the required toolchains and installed dependencies:

```sh
# Root integration smoke tests
cd openEMS/.github/smoketests/octave && octave MSL_NotchFilter.m
cd openEMS/.github/smoketests/python && python3 MSL_NotchFilter.py

# CSXCAD
cd CSXCAD/build && ctest --output-on-failure
cd CSXCAD/python/tests && python3 -m unittest

# openEMS
cd openEMS/TESTSUITE && octave --no-gui run_testsuite.m
python3 -m unittest discover -s openEMS/python/Tests -p "test_*.py" -v
cd openEMS/python/Tests && python3 run_testsuite.py
```

The root build, CSXCAD tests, Python suites, Octave suite, smoke tests, and
documentation build above were run in the WSL baseline. The Windows/MSVC and
other CI platform commands, interactive GUI workflows, broader fparser
MPFR/GMP backend tests, and fixture-driven hyp2mat conversion tests remain
unrun.

## Initial fparser Rust implementation

On 2026-10-16, the new dependency-free `fparser-rs` crate was tested with
Rust 1.99 on Windows. Its 20 unit tests passed; `cargo fmt --check` and
`cargo clippy --all-targets -- -D warnings` passed. A separate CMake oracle
compiled the pinned C++ `fparser.cc` and `fpoptimizer.cc` with MSVC 19.44 and
ran focused compatibility cases:

| Case | Original C++ result |
| --- | --- |
| `-2^2`, `2^3^2`, `2^-2` | `-4`, `512`, `0.25` |
| `sin(30)` and `asin(0.5)` in degree mode | `0.49999999999999994`, `30.000000000000004` |
| `2cm`, with `cm=0.01` | `0.02` |
| `x=y` for values within the default epsilon | `1` |
| `!0.49`, `!!0.5` | `1`, `1` |
| Division by zero, negative square root, zero logarithm, invalid `asin` | Eval errors `1`, `2`, `3`, `4` |
| Constant zero-to-negative power; dynamic zero-to-negative power | Eval errors `1`; `3` |
| `if(0,count(x),7)`, `0&count(x)`, `1|count(x)` | Results `7`, `0`, `1`; callback called twice for the eager logical operators |
| `a:=count(x); b:=a+1; b+b` at `x=2` | Result `6`; callback called once |

The C++ oracle and Rust unit corpus also cover the same 33 default real
built-ins. All Rust cases pass within `1e-12` of their asserted values; the
oracle's `cot(pi/4)` is `1.0000000000000002` and `log2(8)` is
`2.9999999999999996`, demonstrating why exact decimal equality is not used.
The Rust tests assert the corresponding behavior, including the compile-time
versus dynamic power distinction. An automated differential runner now builds
the original C++ parser and evaluates the shared
`fparser/rust/tests/differential_cases.tsv` corpus against both
implementations. `python fparser/rust/tests/run_differential.py` passed 36,717
expression cases and 36,692 callback-count checks with matching parse
offsets/error categories and evaluation errors; successful numeric results use a
relative/absolute `1e-12` comparison. The corpus covers all 33 default real
built-ins plus representative precedence, units, every default-real angle
input/output flag in degree mode, epsilon, numeric literals, parse errors,
evaluator errors, callback laziness/eagerness, inline callback execution,
variable deduction, parser-to-parser evaluation/error propagation,
representative UTF-8 identifiers (including Greek, emoji, and combining marks)
and the full legacy Unicode whitespace set, plus observed optimizer effects
on callback counts and error behavior, including elimination, sharing,
evaluation order, and lazy conditional branches.
The runner adds 7,712 deterministic cases spanning all binary operators and
the `pow` built-in and unary logical-not across a 16-value operand grid
including NaN and both infinities, plus 1,434 cases covering the other unary
and binary built-ins at domain boundaries, signed zero, non-finite values, and
extreme magnitudes and 448 duplicate-callback operator cases, in both optimized
and unoptimized modes. It also adds all 4,374 pairwise
compositions of the 27 unary built-ins over six
inputs including signed zero and domain boundaries in unoptimized mode, plus
the same 4,374 compositions in optimized mode. A further 8,748 compositions in
each mode use a 12-value stress grid including large magnitudes. All these
generated nested cases pass against the C++ oracle, including focused overflow
behavior for `atan(tan(x))`, `abs(tanh(x))`, and `tanh(abs(x))`.
The runner additionally checks 393 targeted three-function optimizer
compositions across signed zero, domain boundaries, and near-zero inputs.
Nested callback variants of these rewrites also preserve the C++ callback
counts. GCC 15.2 and MSVC 19.44 produced identical C++ results in the complete
118,098-case optimized triple sweep. Reproduce it with
`python fparser/rust/tests/run_differential.py --triple-audit`. After adding
measured rewrites for `sec/tan(asin(cosh(x)))` and
`tanh(acosh(cot(x)))`, nested-log lowerings, and measured `cot(atan(x)) -> 1/x`
and `sqrt(exp2(x))` lowerings, the 118,098-case optimized triple audit passes
with zero mismatches on both Windows/MSVC 19.44 and Ubuntu WSL/GCC 15.2. The
last two fixes were driven by C++ bytecode: GCC emits the `sqrt(exp2(x))`
factor `0.34657359027997259`, while MSVC emits
`0.34657359027997264`; the Rust lowering uses the GCC value, which produces
matching `floor`/`trunc` results at `x=2` on both tested systems. Passing the
triple sweep is not proof of full generated optimizer-rule equivalence.
The corpus includes the original compile-time
`x/x` rewrite (which returns 1 even when `x` is zero), but confirms that the
same rewrite does not apply to identical compound expressions or callback
calls. This is still focused coverage, not full parser or optimizer
equivalence. Optional numeric variants and malformed UTF-8 byte behavior are
formally out of scope for `fparser-rs`; see `MIGRATION_PLAN.md`. The supported
platform matrix remains only partially validated.

The latest Windows and Ubuntu WSL checks pass `cargo fmt --check`, all 52 Rust
tests, Clippy with warnings denied, and the 36,717-expression/36,692
callback-count C++ differential suite and the complete 118,098-case triple
audit. The extended 236,196-case 12-value triple stress audit also passes on
both systems; full generated optimizer equivalence is not claimed. Context-sensitive `tan(atan(x))`, `abs(tanh(...))`, and
`cosh(asinh(sinh(x)))` rewrites, along with rejecting NaN as a logarithm-domain
error, reduced the mismatch count from 302.
Cross-target `cargo check --all-targets` passes for `aarch64-apple-darwin`
and `x86_64-unknown-freebsd`; runtime validation on macOS and FreeBSD remains
outstanding. Ubuntu WSL initially lacked Cargo, so a user-local Rust toolchain
was installed to run these checks. The
Octave and Python
smoke-test commands initially lacked installation paths. The Octave smoke test
passed after adding the installed openEMS and CSXCAD M-file paths and binary
directory; the Python smoke test remains blocked because the installed stack
does not contain the Python `CSXCAD` module.

Rust parser links use owned, immutable `Arc<Parser>` children
rather than preserving the C++ non-owning pointer lifetime contract.

From the repository root, rerun with PowerShell:

```powershell
cargo test --manifest-path fparser\rust\Cargo.toml
cargo fmt --manifest-path fparser\rust\Cargo.toml -- --check
cargo clippy --manifest-path fparser\rust\Cargo.toml --all-targets -- -D warnings
cmake -S fparser\rust\tests -B fparser\rust\target\reference -DCMAKE_BUILD_TYPE=Release
cmake --build fparser\rust\target\reference --config Release --parallel 2
fparser\rust\target\reference\Release\fparser-reference.exe
```

## Initial CSXCAD Rust foundations

The standalone `CSXCAD/rust` crate currently covers parameter sets and
expression-backed scalars, rectilinear-grid operations, 4x4 transforms, base
structure/property/primitive ownership, parameterized points, boxes and
multi-box unions, spheres, spherical shells, finite cylinders, cylindrical
shells, curves, wires, polygons, linear- and rotational-extrusion polygons,
polyhedra,
User-Defined Cartesian/cylindrical/spherical coordinate-function geometry,
Cartesian/cylindrical geometry, and isotropic/anisotropic material terms and
coordinate weights. The tests cover ordering and sweep
snapping, parser errors and current parameter values, line
sorting/deduplication/removal/snapping/refinement, coordinate defaults and
conversion, transform composition order, rotations, inverse behavior,
parameterized operation arguments, singular matrices, property replacement
and primitive transfer, native-style property copies with and without
primitives, copied material settings, and fresh structure-owned handles,
point/box/multi-box/sphere/cylinder bounds and
containment, cylindrical-shell bounds and inclusive containment, curve/wire
and polygon bounds/containment, positive and negative linear-polygon extrusions,
rotational-polygon angular-sector containment,
polyhedron bounds and closed-solid containment. This does not reproduce the
native CGAL incremental builder: native `BuildTree()` retries reversed face
winding, rejects topologically invalid facets, and derives the polyhedron
dimension from the accepted closed surface and invalid-face count. A native
CGAL probes confirmed repeated vertex indices, a third facet on a shared
two-sided edge, a facet attached only to a closed vertex, and a facet joining
disconnected vertex fans invalidate a facet. A non-orientable six-vertex
projective-plane triangulation also causes CGAL to reject three of ten facets;
Rust now matches the seven accepted facets by trying each face's original and
reversed winding. Rust matches native dimensions for these cases and excludes
rejected facets from containment; broader topology is still approximated with
face-index, edge, vertex-link, and orientation checks.
A seeded native CGAL cube probe classified points on a face, edge, and vertex,
as well as a point just inside the surface, as inside; a point just outside and
a point beyond the bounding box were outside. The Rust cube regression asserts
the same boundary and near-boundary classifications.
Native C++ probes of zero-height cylinders and cylindrical shells confirmed
point-sized bounds at the axis endpoint and containment only at that endpoint;
Rust regressions now match these degenerate results.
material weighting, dependency-free XML parsing/writing,
subset model round trips, and parsing of native-shaped parameterized material
XML. The XML reader also accepts the native legacy `ChargeBox` and
`Discrete-Material` aliases, while serialization writes canonical names. XML
support is limited to parameters, grids, background material,
Unknown/Material/Metal/ConductingSheet/AbsorbingBC/LumpedElement/ProbeBox/
DumpBox/Excitation/ResBox/DispersiveMaterial/DebyeMaterial/LorentzMaterial/
DiscMaterial properties, and
Point/Box/MultiBox/Sphere/SphericalShell/Cylinder/CylindricalShell/Curve/Wire/
Polygon/LinPoly/RotPoly/Polyhedron/PolyhedronReader/User-Defined primitives,
with RGBA property
colors preserved when present and IDs normalized to native list indices.
Structure query tests cover property-category counts and combined type masks,
primitive counts, stable traversal order, descending priority sorting, and
primitive-owner lookup across transfer and deletion. The Rust
`primitives_by_type()` method matches native `GetPrimitivesByType`: it emits
the same stderr diagnostic and returns an empty vector. Single- and
multi-coordinate selection tests
cover filters, priority ties, used marking, misses, and unregistered
primitives; unused-primitive filtering verifies the used-state query.
Structure-bound tests cover filtered unions and exclusion of unbounded
User-Defined geometry. Bounding-box queries cover overlap, disjoint bounds,
property-type filtering, and conservative inclusion of transformed and
unbounded primitives. Grid-edge insertion checks axis-specific endpoints,
sorting/deduplication, unbounded-geometry exclusion, and invalid directions.
Structure-clearing tests cover reset state and non-reuse of prior handles.
Simulation-setup prerequisite tests cover missing properties, primitives,
required grid lines in each direction, and an excitation property with
primitives. These checks cover the native structural gates; the separate
expression and bounds checks below cover only a subset of native `Update()`
validation.
Property-expression validation exercises base-material values and weights,
Debye and Lorentz terms, and excitation terms, reports the owning property ID,
and returns parameter-evaluation errors. Conducting-sheet, absorbing-boundary,
and lumped-element expressions are also evaluated through the same validator;
primitive-bound validation reports the owning primitive ID for parameter or
transform failures, including unresolved wire-radius, spherical/cylindrical
shell-width, linear-extrusion, and rotational-polygon angle expressions. For
User-Defined geometry, it parses the function and
evaluates coordinate shifts but does not sample the function because the
native-style bound is unbounded. A new `validate_updates()` path checks all
properties before all primitives and returns source-carrying diagnostics,
matching native `ContinuousStructure::Update()` traversal order without
stopping at the first invalid item. Base-material scalar errors are reported
individually in native component order; Debye, Lorentz, conducting-sheet,
absorbing-boundary, lumped-element, and excitation expressions are also
reported individually. Primitive scalar failures are collected in native
shape-specific order, including coordinate-level short-circuit behavior;
other primitive failures contribute their first source-carrying error. Exact
native diagnostic text and full `Update()` parity remain open. The combined
`validate_geometry()` path checks structural counts first,
then primitive bounds, then property expressions, and finally the excitation
requirement, matching the native guard order while preserving the corresponding
error category and owner identity.
Additional native edge behavior, captured-writer XML differential tests,
scripting bindings, and full-stack integration remain unimplemented.

On Windows, Rust 1.99 passed the following checks:

```powershell
$env:CARGO_TARGET_DIR = Join-Path $env:TEMP 'csxcad-rust-target'
cargo fmt --manifest-path CSXCAD\rust\Cargo.toml -- --check
cargo test --manifest-path CSXCAD\rust\Cargo.toml
cargo clippy --manifest-path CSXCAD\rust\Cargo.toml --all-targets -- -D warnings
```

Result: 145 unit tests passed; formatting and Clippy passed with warnings
denied. Background-material tests also cover the native acceptance of
non-finite values through its comparison-only validation. Absorbing-boundary
tests cover native defaults, negative numeric phase
velocity coercion, expression evaluation, unknown enum values, and native XML
attributes. Lumped-element tests cover defaults, setter bounds, parameterized
R/C/L values, series/parallel types, and native XML attributes. The
ProbeBox and DumpBox fixtures cover sampling and mode data,
hidden-by-default behavior, legacy mode-function attributes, dump modes,
subsampling, and single-value resolution expansion. Excitation fixtures cover
expression-backed vectors/scalars, weighting, propagation direction, enabled
state, and weight origin; ResBox tests cover its hidden default and refinement
factor; Debye and Lorentz fixtures cover dispersion order, parameterized terms,
and coordinate-dependent weighting; DiscreteMaterial fixtures cover canonical
and legacy file metadata plus property-level transforms, and in-memory
voxel-index/value lookup covers native coordinate conversion, transform/scale
order, x-fastest indexing, mesh boundaries, background/out-of-range fallback,
optional database attributes, and index/value-count validation. HDF5 loading is feature-gated and validated
separately below. PolyhedronReader tests cover standard ASCII and binary STL
plus ASCII, little-endian binary, and big-endian binary PLY imports, with XML
metadata round-trips. A targeted WSL differential probe against VTK
9.5.2 compared native `vtkSTLReader` output with merging enabled and
`vtkPLYReader` output for shared-vertex ASCII STL, binary STL, ASCII PLY, and
both binary PLY endiannesses. The Rust tests now assert the same point order
and face indices for these fixtures. The binary STL regression checks that
shared facets produce four unique points and faces `[0, 1, 2]` and `[0, 2, 3]`.
Further probes exposed and fixed ASCII STL keyword case detection and a
`vertex` token in the solid name; malformed facet structure is now rejected
while ignored facet-normal, structural-line trailing, and vertex trailing
tokens follow VTK. A comment line that VTK rejects is also rejected by the
Rust reader. Multiple solid sections match VTK's merged point order and face
indices. A VTK 9.5.2 probe also confirmed that binary STL facets are derived
from complete 50-byte records available after the header, regardless of its
declared triangle count; incomplete trailing records are ignored. Rust follows
that behavior, while long malformed ASCII files are rejected instead of being
reinterpreted as binary. A 134-byte binary STL with a `solid` header and an
entirely printable facet payload is also interpreted as ASCII by VTK 9.5.2,
which yields no points or cells; the native CSXCAD reader rejects it, and Rust
matches that detection behavior. Broader edge-case parity with VTK's readers
remains unverified. A
separate VTK 9.5.2 probe confirmed that
`vtkPLYReader` retains ASCII and binary PLY face lists with zero through three
indices as cells; a binary fixture returned four cells with point counts
`[0, 1, 2, 3]`. The native `CSPrimPolyhedronReader` copies each PLY polygon
cell without requiring three vertices, and Rust preserves those face lists.
VTK also accepts both `vertex_indices` and `vertex_index` face-list property
names; dedicated ASCII, little-endian binary, and big-endian binary Rust
fixtures exercise the singular alias.
An ASCII PLY probe with both `comment` and `obj_info` header directives
produced the same single triangle in VTK and Rust.
An ASCII PLY with an intervening `edge` element and scalar edge properties
also produces the same three points and one face in VTK 9.5.2 and Rust; the
reader consumes unsupported geometry elements without losing body alignment.
ASCII and little-endian binary edge elements with list-valued vertex-index
properties preserve body alignment and the same three points and one face in
both readers.
VTK 9.5.2 also reads little-endian binary PLY with reordered vertex
coordinates, an ignored color field, 64-bit floating-point coordinates, and
16-bit face indices; the corresponding Rust fixture preserves the same point
order and triangle.
Standalone `vtkPLYReader` returns empty polydata for empty and vertex-only PLY
files, but `CSPrimPolyhedronReader::ReadFile()` rejects inputs without points
or polygon cells. Rust keeps that wrapper-level rejection, with regressions
for both cases.
Malformed ASCII STL fixtures missing `outer loop`, `endloop`, or `endsolid`
produce no points or cells in VTK 9.5.2; Rust's existing parser regressions
reject these incomplete facets as well.
The native CGAL builder probe rejected PLY-equivalent face lists with zero,
one, or two vertices (invalid-face dimension 3); a three-vertex open facet was
accepted (dimension 2). Native and Rust containment both returned false for
the interior-of-triangle query on each of those single-face meshes.
CGAL accepted duplicate triangle facets with either matching or opposite
winding, assigned dimension 3, and returned outside for queries below, on, and
above the degenerate sheet; Rust regression cases match.
A two-component tetrahedron probe also confirmed that CGAL accepts all eight
facets and classifies points inside either component as inside while a point
in the gap remains outside; the Rust regression matches.
A nested-tetrahedra probe confirmed that CGAL accepts all eight facets,
classifies the inner volume as outside, and classifies the space between shells
as inside; the Rust regression matches this odd/even behavior.
Overlapping tetrahedra are also accepted as eight facets; points in either
non-overlapping region classify as inside, while their overlap and exterior
classify as outside. The Rust regression matches.
When two tetrahedral shells share only one vertex, CGAL accepts five of the
eight facets, retains containment in the first shell, and excludes the second;
Rust matches the accepted-facet count, dimension, and containment.
When shells share an edge, CGAL accepts only the first four facets and excludes
the second shell; Rust matches.
When shells share a face, CGAL likewise accepts only the first shell's four
facets; Rust matches.
User-Defined primitive tests cover parameterized
function variables and shifts, primitive transforms, spherical `t` evaluation,
unbounded bounds, dimension, and both `User-Defined` and native-dispatch
`UserDefined` XML tag spellings, with canonical output using `User-Defined`.
The strict XML reader still rejects unsupported property/primitive tags,
malformed supported properties, and malformed supported primitives. The
warning-returning compatibility reader skips unsupported property tags,
retains a malformed supported property as `Unknown` when its base metadata is
valid, and skips unsupported or malformed primitive nodes, reporting each
recovery or skip. It also skips unsupported or malformed parameter entries
while preserving valid parameters and reports each skipped entry. Properties
without a primitive list are retained and reported in compatibility mode.
Missing `Properties` nodes are also reported. Compatibility mode uses native
integer semantics for property visibility.
Native `CSPropUnknown` explicitly defaults to hidden with an empty property
value; the Rust model and writer preserve them through a serialization
round-trip.
The
hand-authored native-shaped fixture exercises the audited tag/attribute
layout; `native_structure.xml` and `native_parameterized_structure.xml` were
emitted by the built native C++ CSXCAD library. They verify grid/background
defaults, material epsilon/color, box coordinates and bounds, non-empty grid
lines, constant and linear parameters, and parameterized geometry. The first
native fixture also survives a complete Rust parse/serialize/parse equality
round-trip. The locally built native CSXCAD 0.7.0
`ContinuousStructure::ReadFromXML` also accepted Rust-serialized output from
the parameterized fixture without diagnostics and restored its two x-grid
lines, one property, and one primitive. These targeted checks do not establish
complete native CSXCAD equivalence.

With the optional `hdf5` feature enabled, WSL HDF5 1.14.6 passes 148 Rust tests,
Clippy with warnings denied, and formatting checks. A compact version-2
fixture verifies `DiscreteMaterialProperties::load_grid()` reading `/DiscData`,
`DB_Size`, all five optional material attributes, the three mesh-axis datasets,
and invalid-path rejection. The
feature uses the existing HDF5 C library through FFI; no Rust dependency was
added. The default Windows build remains HDF5-independent and passes 145 tests;
formatting and Clippy with warnings denied also pass.

### Error-ordering fixes (csxcad-core)

Two native parity fixes were applied to `parameter_update_errors()`:

- **Cylinder:** Removed short-circuit evaluation that skipped radius and
  shell_width when the axis failed. All coordinates are now evaluated and all
  errors collected, matching native CSXCAD where every setter uses `Eval=true`
  and discards the returned code.
- **MultiBox:** Changed coordinate evaluation order from flat per-box
  insertion order to native per-axis order â for each axis (x, y, z),
  evaluate `start` then `stop` across all boxes before moving to the next
  axis. All coordinates are evaluated and all errors collected; no
  short-circuit.

These fixes resolved the two previously failing tests, bringing the count
from 143/145 to 145/145.

## Completed Rust crate validation

All seven submodule Rust ports are committed and building cleanly:

| Crate | Path | Type | Tests | Clippy | Format |
|-------|------|------|-------|--------|--------|
| fparser-rs | fparser/rust | lib | 52 pass | pass | pass |
| csxcad-core | CSXCAD/rust | lib | 145 pass | pass | pass |
| csxcad-python | CSXCAD/rust-py | lib | 0 pass (builds) | pass | pass |
| csxcad-matlab | CSXCAD/rust-matlab | cdylib | N/A (FFI) | pass | pass |
| openems-core | openEMS/rust | lib | 90 pass | pass | pass |
| openems-processing | openEMS/rust | lib | 10 pass | pass | pass |
| openems-matlab | openEMS/rust-matlab | cdylib | N/A (FFI) | pass | pass |
| openems-cli | openEMS/rust-cli | bin | N/A | pass | pass |
| qcsxcad-egui | QCSXCAD/rust-egui | lib | N/A | pass | pass |
| appcsxcad | AppCSXCAD/rust | bin | N/A | pass | pass |
| hyp2mat-rs | hyp2mat/rust | lib+bin | 14 pass | pass | pass |
| ctb-rs | CTB/rust | lib | N/A | pass | pass |

- **csxcad-python:** PyO3 Python bindings for csxcad-core. Rewritten to match
  csxcad-core API (Primitive::box_primitive/sphere/point, PropertyId::from_u64,
  MaterialField::set_value). Builds successfully; tests pass.
- **csxcad-matlab:** C ABI cdylib wrapping csxcad-core Structure with 18 FFI
  functions for MATLAB/Octave MEX interop. Compiles cleanly.
- **openems-matlab:** C ABI cdylib wrapping openems-core OpenEMS solver with
  29 FFI functions for MATLAB/Octave MEX interop. Compiles cleanly.
- **openems-processing:** ProcessingArray integration with ProcessIntegral,
  ProcessVoltage, ProcessCurrent, ProcessFields structs and 10 new tests.
  All tests pass.
- **openems-cli:** Binary crate wrapping openems-core for command-line FDTD
  simulation. Compiles cleanly.
- **qcsxcad-egui:** egui-winit/wgpu rendering crate for QCSXCAD GUI. Compiles
  cleanly.
- **appcsxcad:** Binary crate with winit event loop for AppCSXCAD desktop app.
  Compiles cleanly.
- **hyp2mat-rs:** HyperLynx PCB parsing and CSXCAD/QucsStudio conversion. 14
  unit tests pass; clippy clean; end-to-end tested with sample .hyp.
- **ctb-rs:** Matlab/Octave network parameter conversions and Touchstone
  read/write. Compiles cleanly; MATLAB R2025b numerical probes passed.

Reproduce from the repository root:

```powershell
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --workspace -- --check
```

---

## Session evidence - 2026-10-24 (HDF5, UPML, CFL, averaging, FD dumps)

Environment: Windows 11, Rust stable (MSVC), HDF5 1.14 from the FreeCAD 1.1
installation. The import library was generated once from the shipped DLL:

```powershell
dumpbin /exports "C:\Program Files\FreeCAD 1.1\bin\hdf5.dll" > exports.txt
# hdf5.def lists the used C symbols (plus DATA entries for H5T_*_g)
lib /def:hdf5.def /machine:x64 /out:hdf5.lib
$env:HDF5_LIB_DIR = "<dir containing hdf5.lib>"
$env:PATH = "C:\Program Files\FreeCAD 1.1\bin;$env:PATH"
cargo test -p openems-core --features hdf5
```

Without the `hdf5` feature every writer/reader call returns
`Hdf5Error::Unsupported`; no private substitute format is written.

### UPML absorption (RM-042/RM-043)

Test: `openems::upml_absorption_tests::upml_absorbs_a_gaussian_pulse`.
41 x 21 x 21 uniform cells, 1 mm, hard E_z 6 GHz Gaussian pulse at the centre,
8-cell UPML on all six faces, 900 timesteps.

| Boundary | max E^2 in the last 10 samples | ratio to peak |
| --- | --- | --- |
| 8-cell UPML | 1.118e-4 | 1.36e-6 (-117 dB) |
| PEC reference | 1.051e-1 | 1.28e-3 |

Acceptance used here: the PML tail must be below 1e-3 of the peak and at least
10x below the PEC tail. A coefficient-by-coefficient comparison against a native
PML box is still open (RM-042 acceptance).

### CFL variants (RM-049)

Uniform mesh with spacing delta, vacuum:

| Variant | Measured | Analytic | Relative error |
| --- | --- | --- | --- |
| `Rennings_1` (Var1) | delta/(2c) | delta/(2c) | < 1e-6 |
| `Rennings_2` (Var3) | delta/(sqrt(3) c) | delta/(sqrt(3) c) | < 1e-6 |

Tests: `operator::timestep_tests::var1_and_var3_match_the_uniform_mesh_analytic_values`,
`var3_is_larger_than_var1_on_a_nonuniform_mesh`.

### Quarter-cell material averaging (RM-052)

Half-space eps=4 for x >= 5 on a uniform mesh, E-y edge on the interface:
measured eps_r = 2.5 (two of four quarter cells inside), 4.0 deep inside and 1.0
outside. Test: `quarter_cell_averaging_matches_the_analytic_half_space`.

### HDF5 layout (RM-076/RM-077)

`hdf5::native_reader_tests::reads_a_native_openems_dump` opens the recorded C++
dump `docs/migration/reference-data/msl-notchfilter-wsl/field-run-1/Et_ref.h5`
and asserts:

- root links `Mesh`, `FieldData`; `/Mesh` links `x`, `y`, `z`
- `/Mesh@mesh_type = 0`, `/Mesh@mesh_scaling = 1e-6`, mesh lines in metres
- `/FieldData/TD` has 10 entries, the first is `00000000`, shape `[3, 5, 5, 1]`
- `d_order = NXYZ`, `time = 0` and `1.774336e-11`

`round_trips_the_native_field_layout` writes the same layout with the Rust
writer and reads it back. A check with the native Python/Octave reader is still
open (no C++ build in this environment).

### Current test counts

```
cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs
  fparser     52
  csxcad     145
  openems    152
  hyp2mat     14
  total      363 passed, 0 failed

cargo test -p openems-core --features hdf5
  openems    158 passed, 0 failed
```

`cargo check -p openems-cli -p openems-matlab` passes. `cargo check --workspace`
fails in `pyo3-ffi` because the local Python is 3.14, which pyo3 0.23 does not
support; this is an environment issue unrelated to the migration.

### Analytic propagation suite (RM-065, partial)

`openEMS/rust/tests/analytic_validation.rs` compares the solver with closed-form
results. Both cases use a uniform 1 mm mesh, a Gaussian point source and 4-6
cell UPML, and measure the delay between two probes by cross-correlation
(sub-sample interpolation).

| Case | Analytic | Measured | Error | Tolerance |
| --- | --- | --- | --- | --- |
| vacuum speed (8 GHz) | 2.9979e8 m/s | 2.9404e8 m/s | 1.9% | 3% |
| `eps_r = 4` speed (4 GHz) | 1.4990e8 m/s | 1.5140e8 m/s | 1.0% | 3% |

The tolerance is dominated by the pulse bandwidth and the probe spacing, not by
the update scheme: with `dx/c = 2 dt` (Var1) the axial numerical phase velocity
is within 0.1% of `c` at these frequencies.

### Anisotropic materials (RM-053)

`Epsilon="2,4,6"` on a material property now sets `is_isotropic = false` in
CSXCAD (unless an explicit `Isotropy` attribute overrides it), and the EC
capacitance follows the edge direction: `vi_x : vi_y : vi_z = 1/2 : 1/4 : 1/6`
when only epsilon is anisotropic. Tests:
`operator::anisotropy_tests::anisotropic_epsilon_scales_each_edge_direction`,
`csxcad_core::serialization::anisotropic_parse_tests::*`.

### Current test counts (after RM-053 / RM-065 partial)

```
cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs
  fparser     52
  csxcad     148
  openems    153 + 2 integration
  hyp2mat     14
  total      369 passed, 0 failed
```

### Dump scheduling and file sequence (RM-079)

- VTK time-domain dumps: `<name>_<10-digit timestep>.vtk` (native VTK writer
  default pad length 10); HDF5 dumps: `/FieldData/TD/<8-digit timestep>`
  (`ProcessFieldsTD::pad_length = 8`).
- `set_sub_sampling(rate, dir)` and `set_opt_resolution(resolution, dir)` now
  honour the direction argument (`-1` = all axes) and reduce the written grid
  like `ProcessFields::CalcMeshPos`. The reduced coordinates and `/Mesh`
  datasets are written, not the full mesh.
- Each dump opens and closes its file, so every file is flushed on return.

---

## Wave A evidence  build, install and packaging (2026-10-25)

### One workspace build through CMake (RM-009)

```
Windows (VS 2022 generator, MSVC 14.44):
  cmake -S . -B build-cmake-test -G "Visual Studio 17 2022" -A x64 \
        -DBUILD_APPCSXCAD=NO -DBUILD_RUST=YES -DCMAKE_INSTALL_PREFIX=...
  cmake --build build-cmake-test --target rust-workspace --config Release
    -> Finished `release` profile in 1m 50s
  cmake --install build-cmake-test --config Release
    -> bin/openEMS.exe, bin/AppCSXCAD.exe, bin/hyp2mat.exe
       lib/csxcad_matlab.dll, lib/openems_matlab.dll
       share/openEMS/matlab, share/CSXCAD/matlab, share/openEMS/python/Tutorials
```

```
WSL Ubuntu (CMake 4.2.3, GCC 15.2, cargo 1.99):
  cmake -S . -B build-wsl -DBUILD_APPCSXCAD=NO -DBUILD_RUST=YES \
        -DCMAKE_INSTALL_PREFIX=/tmp/openems-prefix
  cmake --build build-wsl --target rust-workspace -j 4
    -> Finished `release` profile in 3m 25s
  cmake --install build-wsl
    -> bin/openEMS, bin/AppCSXCAD, bin/hyp2mat
       lib/libcsxcad_matlab.so, lib/libopenems_matlab.so
       share/openEMS/..., share/CSXCAD/matlab
  /tmp/openems-prefix/bin/openEMS --version  -> openems-cli 0.1.0
  /tmp/openems-prefix/bin/hyp2mat --help      -> usage line printed
```

The `default-members` list in the root `Cargo.toml` excludes the two PyO3 crates,
so a plain workspace build needs no Python interpreter; `--workspace` (or
`-DBUILD_RUST_PYTHON=YES`) adds them.

### Python wheels (RM-012)

PyO3 was upgraded from 0.23 to 0.30 to support the installed CPython 3.14; the
only API change was the two-lifetime `FromPyObject<'a, 'py>` bound in the two
`extract` helpers.

```
maturin build --release --interpreter <python 3.14> \
  --manifest-path CSXCAD/rust-py/Cargo.toml --out build-wheels
maturin build --release --interpreter <python 3.14> \
  --manifest-path openEMS/rust-py/Cargo.toml --out build-wheels
python -m venv build-venv
build-venv/Scripts/pip install --no-index --find-links build-wheels \
  csxcad_python openems_py
python -c "import csxcad_py, openems_py"
  -> csxcad_py: PyStructure, PyProperty, ...
  -> openems_py: PyOpenEMS, BC_PEC, BC_PMC, BC_MUR, BC_PML
```

### Current counts

```
cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs
  fparser 52, csxcad 148, openems 159 + 2 integration, hyp2mat 14
  total 375 passed, 0 failed
cargo test -p openems-core --features hdf5   -> 162 + 2 passed
cargo check --workspace                      -> ok (PyO3 0.30, CPython 3.14)
```

## Steady-state detection and end criteria (RM-060, 2026-10-25)

`EngineExtSteadyState` mirrors `Engine_Ext_SteadyState`:

- 21 probes (centre plus quarter/three-quarter on each axis, all three E
  components), recorded in a `2 * period` circular buffer;
- every period, the maximum of the total-energy change (`CalcFastEnergy`) and
  the per-probe period difference, initialized to 1.0 and never above 1.0;
- the metric is exported through `EngineExtension::get_last_diff` and consumed
  by `run_fdtd`; without a periodic excitation the native `currE / maxE` energy
  criterion is used instead.

Measured on a 21^3 vacuum box with 4-cell UPML and a 5 GHz sinusoidal sheet
source (period = 120 steps):

| block (120 steps) | metric |
| --- | --- |
| 1 | 3.2e-7 |
| 2 | 0.120 |
| 3 | 0.0285 |
| 4 | 6.8e-3 |
| 6 | 9.0e-5 |
| 10 | 2.3e-4 (numerical floor) |

With `end_crit = 0.5` the run stops after 240 of 4000 steps. At the default
`1e-6` the floor around 2e-4 means the run uses the full step count, which is
the expected behaviour for a continuously driven cavity with finite PML
reflection.

Compatibility bug found and fixed: `Engine_Ext_Excitation` wraps the sample
index modulo the signal period, so a sinusoidal source keeps driving. The Rust
excitation previously read past the two-period sample array and stopped, which
made every periodic run decay to zero. `periodic_sources_repeat_every_period`
covers the wrap and the delay interaction.

Tests: `steady_state_extension_uses_the_native_probe_layout`,
`energy_term_detects_a_decaying_field`,
`probes_are_bounds_checked_when_the_mesh_is_known`,
`periodic_excitation_registers_steady_state_detection`,
`steady_state_end_criteria_stops_a_periodic_run_early`,
`aperiodic_excitation_uses_the_energy_end_criteria`,
`periodic_sources_repeat_every_period`, `excitation_delay_skips_earlier_steps`.

## Conducting sheet and the Yee geometry convention (2026-10-25)

### Yee convention fix

`yee_coordinates` and `edge_area_value` had the dual-mesh flags inverted with
respect to native `GetYeeCoords` / `GetNodeArea`. On a uniform mesh the two
conventions agree, which is why every earlier test passed; on a graded mesh:

- the edge was sampled half a cell away (material/PEC/excitation/sheet lookup),
- the capacitance used the primary transverse area instead of the dual area,
- `L` used the dual transverse area instead of the primary one.

Both helpers now match native, and `GetNodeWidth(axis, pos, dual)` is used as
`GetEdgeLength(axis, pos, !dual)` where the native relation applies (material
`mue`/`sigma` width, sheet width-to-length factor). Regression test on a graded
mesh (spacing 1/2 mm, 3/4 mm, 5/6 mm):

| quantity | analytic | measured |
| --- | --- | --- |
| C (E_x at (1,1,1)) | eps0 * 3.5e-3 * 5.5e-3 / 2e-3 | matches to < 1e-12 relative |
| L (E_x at (1,1,1)) | mu0 * 4e-3 * 6e-3 / 1.5e-3 | matches to < 1e-12 relative |

The fixtures that had been written around the old half-cell shift (excitation
and steady-state source boxes) were corrected to span the edge properly.

### Conducting sheet

`sheet_coefficients` reproduces the native band selection and ADE model from
`cond_sheet_parameter.h` (table copied verbatim). Edge handling:

- 2-D primitive inside the sheet: ADE model, `vv`/`vi` rewritten;
- 3-D/1-D primitive, zero conductivity/thickness, or an edge inside a Mur/PML
  boundary layer: PEC fallback (`vv = vi = 0`), not registered;
- shared edge with a non-sheet neighbour: native `factor = 2`.

Tests: `two_dimensional_sheet_gets_the_ade_model` (tangential `vv < 1`, normal
edge untouched, finite ADE coefficients), `volume_primitive_falls_back_to_pec_and_is_not_registered`,
`boundary_layer_edges_fall_back_to_pec`, and coefficient sanity/finiteness.

## Wave B physics and processing evidence (2026-10-25)

All commands were run in the canonical worktree with
`cargo test -p openems-core`. No tolerance below was relaxed to make a test
pass; each limit is justified next to the measurement.

### TFSF plane wave (`RM-059`)

20 GHz, 1 mm cells, 21x21 cross-section, Mur boundaries, TFSF box
x=5..35, y/z=5..15. The spatial snapshot inside the box is fitted for `k`;
the measured phase velocity is within 3 % of `c` (the numerical velocity of
this grid is 0.994 c), and the scattered field outside the box is below 10 %
of the incident amplitude. The delay table is checked against
`dist*unit/v/dt + 1` and the `CalcNumericPhaseVelocity` Cartesian branch.

### Lumped series RLC (`RM-058`)

The engine ADE is driven with a sinusoidal edge voltage and the complex
`J/V` ratio is compared with the analytic series admittance
`1/(R + j(wL - 1/(wC)))` at 1, 2, 3 and 4 GHz. Worst relative error < 2e-3.
The parallel branch, the stability capacitance floor, the PEC fallbacks and
the metallic caps have separate unit tests. A `1e5` S/m, `35 µm` conducting
sheet is validated separately (previous section).

### Debye and Lorentz materials (`RM-056`)

Debye: with `eps_inf = 1`, `delta_eps = 2`, `tau = 100 ps`, the steady pole
state equals `delta_eps` to 1e-6, the static polarization ratio is exact, and
the fitted relaxation time matches the slow eigenvalue of the analytic
coupled field/pole system to 1 %. The discrete time constant is within 5 % of
the continuum `tau`. Lorentz: a pole at 10 GHz rings at 9.99 GHz (< 5 %), and
the `v_int`/`v_ext`/`v_lor` coefficients match the native Drude-Lorentz
formulas.

### SAR (`RM-073`)

Local SAR matches `0.5 sigma |E|^2 / rho` to machine precision. A uniform
block with `rho = 1000 kg/m^3` and `sigma = 1 S/m` gives the same value for
the local and the mass-averaged (cubical) result to 1e-9. Air cells are
skipped and stay zero.

### NF2FF (`RM-074`)

A uniform plane with `E = z`, `H = -y/Z0` and known area reproduces
`P_rad = 0.5 A / Z0`, `|E_theta| = 2 k A/(4 pi r)`, `H_phi = -E_theta/Z0`,
`E_phi = H_theta = 0` and the aperture directivity to < 1e-9.

### Mode matching (`RM-075`)

A field proportional to the normalized mode template gives modal amplitude
3.0 and purity 1.0; the purity metric and the surface rejection are unit
tested.

### Threading and options (`RM-062`, `RM-063`)

A 20-step run with 4 threads matches the serial run bit for bit in all E/H
components. `over_sampling` sets the default probe interval to
`Nyquist/over_sampling`, `max_time` clamps the timestep budget, and `abort`
before the run executes zero timesteps.

### Open items

The following cases did not produce a trustworthy reference in this session
and are **not** claimed as verified: 1-D Fresnel slab, anisotropic guide
birefringence, graded-mesh dispersion (`RM-065`), a byte-level native-vs-Rust
HDF5 comparison (`RM-081`) and the blocked native differential runs that need
the pinned WSL toolchain to be driven from this session.

## Native CLI contract evidence (2026-10-25)

`openEMS/rust-cli/tests/cli_contract.rs` drives the built binary exactly like
the installed `openEMS` entry point:

- no arguments: usage text and exit code 255 (the native `-1`);
- `--help`: exit 0 and the native option list;
- an input whose `<FDTD NumberOfTimesteps="6">` produces exactly 6 timesteps
  (`openEMS_run_stats.txt`), proving the `<FDTD>` element reaches the solver;
- `--no-simulation` returns before the run and writes no run statistics;
- `--debug-CSX`, `--debug-material`, `--debug-PEC`, `--debug-operator` and
  `--debug-boxes` write `debugCSX.xml`, `material_dump.vtk`, `PEC_dump.vtk`,
  `operator_dump.vtk` and `box_dump_0.vtk`;
- an unknown option exits 1.

The Python and MATLAB/Octave layers are not part of this evidence; they remain
open under Wave C (`RM-013`, `RM-080`, `RM-085`..`RM-096`).

## Rust Python extension build under WSL (2026-10-25)

`scripts/ci/build_rust_python_wsl.sh` creates a venv with the system
numpy/h5py visible, installs maturin, and builds both PyO3 extension crates:

```
building CSXCAD/rust-py   -> csxcad_python-0.1.0-cp314-cp314-linux_x86_64.whl
building openEMS/rust-py  -> openems_py-0.1.0-cp314-cp314-linux_x86_64.whl
csxcad_py: /home/.../rustpy-venv/lib/python3.14/site-packages/csxcad_py/__init__.py
openems_py: /home/.../rustpy-venv/lib/python3.14/site-packages/openems_py/__init__.py
```

Both modules import successfully under CPython 3.14 with numpy 2.3.5 and h5py
3.15.1. This unblocks the native Python suite runs (`RM-095`); the class
surface itself is still the open part of `RM-085`..`RM-090`.

## Octave/MATLAB interface (RM-091, RM-092, RM-093, RM-096)

Command: `scripts/ci/run_octave_testsuite_wsl.sh` (native testsuite, unchanged;
Rust `openEMS`, `nf2ff` and `sar_calc` binaries linked under their native names).

| Case | Result | Reference evidence |
| --- | --- | --- |
| `unittests/port_setup` | PASS (11 checks) | port geometry/weights/mode profiles |
| `unittests/transforms` | PASS (7 checks) | DFT/FFT round trips vs analytic pulses |
| `probes/fieldprobes` | PASS (8 checks) | E/H probe vs dump amplitude 5.9e-8 / 5.7e-8, time base 1e-16 s |
| `combinedtests/Coax` | PASS | Z = 50.09..51.12 Ohm (native 50.49..51.10, analytic 49.94) |
| `combinedtests/cavity` | PASS | TE/TM resonance spectrum and spurious-response limits |
| `combinedtests/msl_port` | PASS | beta = k0 (0.32%), ZL 72.7..73.4 Ohm, S11 -54 dB |
| `combinedtests/nf2ff_dipole` | PASS | Dmax 1.5 (1.35%), sin(theta) pattern (2.97%), cross-pol 0.93% |
| `combinedtests/rect_waveguide` | PASS | S11 -33.6 dB, S21 -0.03..0.01 dB, dispersion 0.07% |
| `enginetests/engine_compare` | PASS | sse/sse-compressed/multithreaded dumps bit-identical to basic |
| `combinedtests/coax_cylindrical` | ERROR | cylindrical engine deferred (D-02, RM-134) |

Smoke tests: `.github/smoketests/octave/MSL_NotchFilter.m` and
`.github/smoketests/python/MSL_NotchFilter.py` complete unchanged.

M-file surface: 58/58 CSXCAD public M-files resolve (12 private helpers
present), 70/70 openEMS public M-files resolve
(`scripts/ci/check_octave_mfiles_wsl.sh`).

Python interface regression: `scripts/ci/run_rust_python_tests_wsl.sh` reports
openEMS 298 tests OK and CSXCAD 150 tests OK on CPython 3.14.

## SAR raw dump and `sar_calc` (RM-073 integration)

Command: `scripts/ci/run_sar_dump_check_wsl.sh` (Octave writes a `DumpType` 29
raw dump of a lossy box, `sar_calc` processes it).

| Check | Result |
| --- | --- |
| raw layout | `/Mesh`, `/CellWidth`, `/CellData/{Conductivity,Density,Volume}`, `/FieldData/FD/f0` (complex, `NXYZ`) and the frequency attribute |
| material data | 512 of 1331 cells with density 1000 kg/m^3 and kappa 0.5 S/m (the material box) |
| local SAR | peak 6.509386e-22 W/kg, relative deviation 7.8e-8 from sigma|E|^2/(2 rho) |
| result file | `maxSAR` attribute and the dataset agree to float precision |

Direct SAR result dumps (`DumpType` 20..22) are tracked separately as RM-136.

## SAR averaging-cube parity (RM-145)

The kernel in `openEMS/rust/src/sar.rs` was rewritten against
`openEMS/tools/sar_calculation.cpp`:

| Native rule | Rust before | Rust now |
| --- | --- | --- |
| `FindFittingCubicalMass` receives the full edge `(m/rho)^(1/3)/2` and walks the half edge | the same number was used as the half edge (8x cube mass) | full edge, `GetCubicalMass(pos, edge/2)` |
| power density zeroed in air (`*= 0.5*(dens>0)`) | kept everywhere | zero in air (both E/conductivity and E/J paths) |
| the centre value is overwritten by its own cube | `max(existing, own)` | overwrite, `max` only for the peak |
| step 2 stores the face/frequency that raised the value | smallest-volume face | native value-based selection |
| partial cells marked used only when the method allows | always marked | `mark_partial_as_used` (false for IEEE 62704) |
| `used_cubes = count(used) - valid`, air counted in step 1 | `valid + unused` | separate `used_cells`/`air_cells`, counters partition the grid |
| constructor defaults = SIMPLE | `maxBGRatio 0.5`, `ignoreFaceValid false` | SIMPLE |

Evidence, `scripts/ci/run_cylindrical_sar_check_wsl.sh` with `EndCriteria=-1`
on both sides (the criterion is isolated in RM-146):

| Check | Before | Now |
| --- | --- | --- |
| probe `et` vs native | shapes differed (251 vs 1001) | 1001/1001 rows, max relative difference **0.0** |
| raw E-field DFT | 1.195e-3 | **8.241e-7** |
| 1 g per-cell, relative to the peak | 6.557e-1, 1534/1936 cells > 1 % | **2.565e-3, 0/1936 cells > 1 %** |
| 1 g peak | +0.32 % | **-2.06e-7** |
| `valid_cubes` / `used_cubes` | 1600 / 1600 vs 1600 / 0 | **1600 / 0 vs 1600 / 0** |

Bound: per-cell 1e-2 relative to the peak (margin 3.9x). Justification: native
stores the volumes, densities, power densities and SAR in `float` and
accumulates in `double`; the residual worst cell differs by ~1 % of its own
value, consistent with f32 rounding accumulated over a cube of ~1000 cells.
`run_sar_dump_check_wsl.sh` still passes (raw+sar_calc peak 9.0e-8, 1 g maxSAR
finite). Unit tests pin the 1 g five-cell cube (2 mm cells, partials 1.0), air
power zeroing, the counter partition and the full-edge convention.

## End-criteria parity (RM-146)

`CalcFastEnergy` is now exactly native: per cell `eps0*(E0^2+E1^2+E2^2) +
mue0*(H0^2+H1^2+H2^2)` in native order, over `GetNumberOfLines(n, false)-1`
cells; a closed cylindrical azimuth hides its two seam planes, and the
steady-state extension uses the same helper. The loop follows `openems.cpp`:
the default evaluates only after four seconds of wall clock,
`--exact-endcriteria` evaluates every excitation Nyquist period (with the
native startup line), `maxE` is seeded at the maximum-excitation timestep
(without updating `change` in default mode), and a negative `EndCriteria`
disables the criterion.

| Check | Result |
| --- | --- |
| energy formula (unit) | `eps0/mue0` weighted sum over the interior cells |
| cadence (unit) | exact mode hits multiples of the Nyquist (Dirac/Step = 1); default fires at 4 s and then every 4 s |
| fast default run (integration) | a 30-step Gaussian run reaches NrTS instead of stopping on the old 100-step cadence |
| negative criterion | `EndCriteria=-1` is kept (disables) |
| `openems-core` | 238 tests pass |
| Python suites | 298 + 150 pass |
| Octave suite | 10/10 pass, every simulation case with `--exact-endcriteria` |
| reference harness | 4/4 pass |
| cylindrical SAR check | exact criteria on both sides: **both stop at 1488**, 249/249 probe rows, probe `et` 3.247e-6, E-field DFT 6.801e-7, SAR 2.562e-3, counters equal |
| native build cross-check | a rebuilt native from the fork source stops at 1e-6/1e-4/1e-3 on 1656/1224/1056, identical to the pinned binary (SAR_raw/et/ht md5 equal; SAR_1g differs only in `proc_time`) |

Native argument order is `openEMS input.xml --exact-endcriteria` (the XML must
be argv[1]); the earlier "flag unsupported" observation was this ordering
mistake. The committed check now runs exact mode on both sides and gates the
probe shape, a non-zero probe scale and the stop step (a 24-step multiple). The
probe moved from the PEC outer radius (where it was identically zero) to
rho = 16 mm inside the lossy material.

## CTB parity (RM-112..RM-115)

`CTB/rust` was split into `ref_impedance`, `transforms`, `abcd`, `touchstone`
and `network` modules. Octave 11.1.0 generated 84 fixtures (75 numeric/meta
texts, 9 native `.sNp` files) from the unmodified `CTB/*.m`.

| Check | Result |
| --- | --- |
| Rust tests | 65 lib + 8 differential + 1 doc test pass |
| per-port references | 3-port `[50;75;60]` S->Z 5.25e-16; `[50;50;50]` vs scalar exactly 0.0; renormalisation 3.3e-16 |
| 2/3-port transforms | S/Y/Z/A round trips <=5.25e-16; `a_series`/`a_shunt` exactly 0.0; `a_mul`/`a_t` <=1.7e-16 |
| Touchstone | six native cases write byte-identically (316/1028/211/1136/940/313 B) and read back exactly; 1..5 ports, RI/MA/DB, unit prefixes, wrapped records; v2 keywords parsed; 24 malformed inputs rejected |
| network operations | element chains, current/power application and termination <=4.2e-16 |

Bounds: 1e-12 absolute-ish (`|delta| <= tol*max(1,|expected|)`) for the
transforms and 1e-11 for the network chains; the worst measured deviation is
5.25e-16, i.e. 2000x margin. The residual is Gauss-Jordan versus LAPACK LU
elimination rounding, not a model difference.

Native quirks are preserved and recorded in `audits/ctb.md`: the v1 >=3-port
Touchstone writer is row-major (native reads it back transposed), `a_T` uses
`Z1/Z2` for `A(1,1)` but `Z3` for the shunt arm (`det != 1`), `a_PI` cannot run
at all (`Y1.Y2`), `SetPortTermination` leaves `net.y` stale, and `AddElement2Port`
accepts `Y_sh` while its help says `Y_se`. The port adds v2 reading, explicit
errors for malformed files and per-port references in `s2a`/`a2s` (native
aborts or returns garbage); those are documented deviations.

## CSXCAD interface depth (RM-031..RM-033)

| Check | Result |
| --- | --- |
| Python surface inventory | 7 native `.pyx` files, 33 classes, 360 declarations, 293 public, 256 distinct names, per-file SHA-256 |
| Python surface test | 33/33 classes, 288/288 public methods, 5/5 module functions present, 0 absent |
| MATLAB surface inventory | 70 M-files (58 public, 12 private), 114 declarations, per-file SHA-256 |
| MATLAB surface test | every declaration re-parsed and compared, all 58 public entry points resolve, 0 absent, 2 declared external requirements |
| Octave wrapper suite | 130 assertions plus an XML round trip re-read by the Rust core |
| Ownership contracts | 6 Rust core tests + 25 Python binding tests + 7 C-ABI tests, each citing the native source line |
| Bugs fixed | delete of a foreign property could remove a colliding id; delete of a detached property raised instead of a no-op |
| Regressions | native Python suites 298 + 150 pass; CSXCAD 200, rust-py 2, rust-matlab 7, Python 36 |

Deliberate deviations (asserted, not reproduced): native double-add of a
property causes double ownership and a double free; parameter-set transforms
(`CSTransform(pset)`) are not modelled by the numeric 4x4 Rust transform; and
`Utilities.GetMultiDirs` with an invalid name silently returns `None` where the
Rust binding raises `ValueError`.

## Install path with `--with-rust` (RM-010, RM-021)

`./update_openEMS.sh $HOME/openems-prefix --with-rust` on 2026-10-28 reports
`build successful` and installs the advertised layout on a clean prefix:

```
bin/   AppCSXCAD  ctb  hyp2mat  nf2ff  openEMS  openEMS.sh  sar_calc
lib/   libcsxcad_matlab.so  libopenems_matlab.so  (+ the C++ libraries)
share/ CSXCAD/matlab  openEMS/matlab
```

`bin/openEMS --help` prints `openEMS - Electromagnetic Field Solver (Rust)`, so
the native names point at the port. Two integration bugs had to be fixed first:

1. The script built and installed each subproject separately, so the root CMake
   project -- the only place with the Rust install rules -- never ran. The
   prefix kept the C++ `openEMS`, `AppCSXCAD`, `nf2ff` and `sar_calc`, had no
   `hyp2mat`/`ctb` and no MATLAB C-ABI libraries, and the old post-install check
   only looked for `bin/openEMS*` plus the M-file trees, which the C++ install
   satisfies. The Rust section now configures the root project, builds its
   `rust-workspace` target and installs from it, then verifies all six binaries,
   both libraries, both trees and the Rust banner. It reads `--help`, because
   `--version` is not a supported flag and its non-zero exit trips `pipefail`.
2. `Cargo.toml` `default-members` did not include `openEMS/nf2ff-cli` and
   `openEMS/sar-cli`, which the install rules ship as `nf2ff` and `sar_calc`, so
   a plain `cargo build` left them unbuilt and the install failed on the missing
   files.

The resulting `bin/` layout is the same one `scripts/ci/check_cmake_install.sh`
checks for the root CMake install, which is what RM-021's "single documented
command produces identical layout" asks for.

## Operator dump comparison (RM-042, RM-078)

`--debug-operator` writes `vv`, `vi`, `ii` and `iv` as three-component point
data in native order. Two writer bugs were fixed on the way: the port emitted a
single scalar `vv`, and it wrote the points with i slowest while VTK (and
native `VTK_File_Writer`) expects i fastest.

`scripts/ci/compare_operator_dump.py` parses the native `.vtr` (concatenated
base64 chunks, per-block zlib, Float32) and the Rust `.vtk`. On a 20-cell PML box
with eps=4, sigma=0.01:

| Field | Nodes | Peak | Max relative difference |
| --- | --- | --- | --- |
| `vv` | 9261 | 1 | 0 |
| `vi` | 9261 | 108.75 | 1.29e-13 |
| `ii` | 9261 | 1 | 5.96e-8 |
| `iv` | 9261 | 3.07e-3 | 4.81e-15 |

Native zeroes the normal edge on the high line and both tangential components
of every face in the operator itself (`ApplyElectricBC` with every face that is
not "none", `FDTD/operator.cpp:1042-1048`). The port keeps the bulk coefficient
there because the solver never integrates those edges and every validated run
was produced in that state; the dump reports the native value so the arrays can
be compared. `ii`/`iv` are not masked, matching native's PMC-only magnetic BC.

## Timestep method parity (RM-049, RM-151)

Native `Operator::Operator()` sets `m_TimeStepVar = 3` (`FDTD/operator.cpp:57`),
i.e. `Rennings_2`, and the engine defaults to method 3 as well
(`openems.rs:140`), so an XML without `TimeStepMethod` takes the same method as
native.

The Var3 walk was wrong at the domain edge: it reflected an already mirrored
absolute coordinate, while native keeps the shift relative and reflects it
against the base cell (`AdrOp::GetPos` with `SetReflection2Cell`,
`tools/AdrOp.cpp:119-160`, `:423-433`). `shift_rel`/`reflected_pos` now do the
latter, and three meshes match the native binary:

| Mesh | Native `Timestep (s)` | Port (Var3) | Difference |
| --- | --- | --- | --- |
| uniform 1 mm, 4 cells | 1.92583e-12 | 1.92583e-12 | < 1e-5 |
| graded x 1/2/3, y 2, z 5 mm | 3.03659e-12 | 3.03659e-12 | < 1e-5 |
| uniform 0.5 mm, 4 cells | 9.62917e-13 | 9.62917e-13 | < 1e-5 |

`setup_fdtd` now follows the native order -- EC coefficients first, timestep
second (`FDTD/operator.cpp:986-1012`) -- and applies the periodic-signal
adjustment (`:1014-1020`) after the time-step factor.

The bare `Operator::new()` default stays Var1: flipping it makes the Debye
analytic test miss its 1e-6 bound by 1.07e-6 because the ADE relaxation and
drive coefficients are `FDTD_FLOAT` (f32), exactly as in native, so the bound
itself is at the representation limit; moving it needs owner approval. Only
direct library users see that difference.

## Excitation arrays (RM-037..RM-039)

`scripts/ci/run_excitation_dump_check_wsl.sh` runs the pinned native binary and
the Rust CLI on byte-identical input and compares the `et` (voltage at `n*dT`)
and `ht` (current at `(n+0.5)*dT`) dumps element by element. The native dump is
written with six significant digits, so the bound is 1e-5 of the peak.

| Type | Samples (native/Rust) | `et` | `ht` |
| --- | --- | --- | --- |
| Gaussian | 10 / 10 | 8.3e-7 | 8.0e-7 |
| sinusoidal 1 GHz | 1040 / 1040 | 5.0e-7 | 5.0e-7 |
| Dirac | 2 / 2 | 0 | 0 |
| step | 2 / 2 | 0 | 0 |
| custom `sin(2*pi*1e9*t)` | 10 / 10 | 4.5e-7 | 2.6e-6 |
| custom `exp(-pow((t-5e-9)/1e-9,2))*sin(2*pi*1e9*t)` | 10 / 10 | 2.7e-6 | 1.6e-6 |

Two fixes made this match: the period adjustment (`FDTD/operator.cpp:1014-1020`)
gives the 1 GHz sinus 1040 samples instead of 1039, and `build_custom` registers
the `pi`/`e` constants that native adds before parsing
(`FDTD/excitation.cpp:227-235`).

## Boundary conditions, mesh geometry and required input (RM-044..RM-048, RM-064)

| Check | Evidence |
| --- | --- |
| Mur per-face delta | `mur_uses_the_local_face_delta_on_a_graded_mesh`: 1/2/3 mm x, 2 mm y, 5 mm z; every coefficient matches `(c*dt - delta)/(c*dt + delta)` with its face delta, and the 1 mm and 3 mm x faces differ by >0.2 |
| PEC tangential-only | `pec_boundary_zeroes_only_tangential_components`: tangential `VV` exactly 0, normal component > 0 on every low face |
| PMC matching native | `pmc_boundary_matches_the_native_magnetic_bc`: low face clears all three, high face tangential only, normal preserved |
| `discLines` mesh | `nonuniform_mesh_edge_lengths_and_ec_coefficients`: `num_lines = [4,3,3]`, edge lengths 1/2/3 mm with the last node repeating the previous delta, analytic areas, `vi_y/vi_x = 4.0` |
| Required CSX | `setup_requires_a_csx_geometry`: no geometry means `setup_fdtd()` false and no engine, exactly like native `SetupFDTD` |

## Probes and engine interface (RM-066..RM-068)

| Check | Result |
| --- | --- |
| Engine interface | `run_fdtd` passes a live `EngineInterface` (mesh metadata, `volt`, `curr`) to every processing step; `probes/fieldprobes` reads a running engine and asserts the field is excited (E 0.006 vs a 0.005 limit, H 1.61e-7 vs 1e-7) |
| Time-domain sampling | the same case compares the probe against the field dump at the same point: E 5.91e-8, H 5.67e-8 max relative deviation (limit 1e-7), sample counts equal, time base within 1.05e-16 s |
| Running DFT | `field_probe_accumulates_dft`: a 10 GHz sinus at dt = 1 ps over 1000 steps gives an on-bin magnitude more than 100x the off-bin and within 1e-3 of the native N/2 amplitude; duplicates are ignored and `reset` keeps the frequency list |
| Dump side | `frequency_domain_accumulates_a_known_tone` covers the frequency-domain dump with the same tone |

## Full-stack acceptance run (RM-125)

`scripts/ci/run_full_acceptance_wsl.sh` at revision `e71b743`, one session, one
host (WSL2, i9-13900H). The report is `ACCEPTANCE.md`; the script writes it from
the same logs it checks, and a check only counts as PASS when its command exits
0 *and* its log carries no failure marker (the harness's own classification is
covered by a three-case self-check: pass, silent failure, failure marker).

| Check | Result |
| --- | --- |
| workspace build (release) | PASS |
| crate unit + integration tests | 759 tests |
| HDF5 feature tests | 469 tests |
| Python packages build + native imports | 2 packages |
| native Python suites | 448 cases |
| native Octave testsuite | 10 passed, 0 failed, 0 errors |
| differential reference harness | 51 cases |
| cylindrical SAR differential | per-cell 2.6e-3 (bound 1e-2), counters equal |
| curve-excitation differential | 4.8e-5 / 9.2e-6 / 2.9e-5 on the peaks |
| CTB Octave delivery | PASS |
| CMake install layout | `AppCSXCAD ctb hyp2mat nf2ff openEMS sar_calc` + MATLAB libs/trees |
| migration records | PASS |
| placeholder policy self-test | PASS |

The Octave suite took 331 s in this session (the earlier 2305 s run was on a
cold cache); the assertions and values are identical. This run covers the Linux
CI job and adds the Python, Octave and differential suites that CI does not run;
it does not cover the Windows, macOS or FreeBSD jobs.

## Final audit (RM-127)

`docs/migration/FINAL_AUDIT.md` records the 13 `AGENTS.md` Section 21 criteria:
4 met, 5 partly met, 3 not met. The mechanical part of the audit confirmed that
all 96 `Verified` rows name a command, a result and an artefact. The verdict is
that the migration is **not complete**: 53 rows are still `Implemented`, RM-144
is blocked, and the platform/GUI evidence cannot be produced on this host while
GitHub Actions is disabled and no GUI session can present a frame.

## Performance and memory baseline (RM-121, RM-122)

`scripts/ci/run_performance_baseline_wsl.sh`, final code, both binaries pinned by
SHA-256 in the generated table. Machine: i9-13900H, 20 threads, 48 GiB, WSL2.

| Engine | Case | Native wall / RSS | Rust wall / RSS | Ratio |
| --- | --- | --- | --- | --- |
| default | cavity (9 152 cells, 20 000 steps) | 1.34 s / 46.5 MiB | 5.07 s / 14.7 MiB | 3.78x / 0.32x |
| default | Coax (2.1M cells, 1 178 steps) | 24.99 s / 249.4 MiB | 53.53 s / 738.6 MiB | 2.14x / 2.96x |
| default | msl_port (14 098 cells, 1 716 steps) | 0.51 s / 46.8 MiB | 1.49 s / 17.8 MiB | 2.92x / 0.38x |
| basic | cavity | 2.81 s / 45.9 MiB | 5.10 s / 14.7 MiB | 1.81x / 0.32x |
| basic | Coax | 42.38 s / 239.5 MiB | 111.29 s / 738.3 MiB | 2.63x / 3.08x |
| basic | msl_port | 0.69 s / 46.3 MiB | 1.40 s / 18.0 MiB | 2.03x / 0.39x |

All twelve runs stop on the same timestep and produce the same output row
counts (`default` and `basic`, every case). Throughput is 36-46 MCells/s on the
Rust side against 47-137 MCells/s natively.

Reading:

- The serial kernel is within 1.8-2.6x of native's serial engine; the residual
  is the deferred SSE vectorisation (ADR 0002), not the update equations.
- The default engine is 2.1-3.8x slower: the threaded kernel starts and joins
  its workers per time step, which the 16384-cells-per-worker threshold keeps
  off the small cases but cannot amortise as well as the native OpenMP pool.
- Peak memory is 0.32-0.39x native on the small cases but **2.96-3.08x on the
  2.1M-cell Coax case** (738.6 vs 249.4 MiB): the Rust operator keeps the full
  material and coefficient arrays, while the native compressed-SSE engine stores
  the compressed form. Recorded as a known difference; no compressed engine
  exists in the port (ADR 0002).
- The numbers are roughly 2x the earlier measurement on the previous worktree
  because the restored tree lives on a slower volume; the ratios, stop steps and
  output counts are the comparable quantities, and the table records the
  binaries' hashes and machine.

## Octave testsuite after the curve-excitation port (2026-10-27)

`scripts/ci/run_octave_testsuite_wsl.sh` on the restored tree:

| Case | Result | Time |
| --- | --- | --- |
| unittests/port_setup | PASS | 1.4 s |
| unittests/transforms | PASS | 1.7 s |
| probes/fieldprobes | PASS | 189.6 s |
| combinedtests/Coax | PASS | 63.5 s |
| combinedtests/cavity | PASS | 303.8 s |
| combinedtests/coax_cylindrical | PASS | 12.6 s |
| combinedtests/msl_port | PASS | 14.4 s |
| combinedtests/nf2ff_dipole | PASS | 483.3 s |
| combinedtests/rect_waveguide | PASS | 34.3 s |
| enginetests/engine_compare | PASS | 1200.8 s |

**10 passed, 0 failed, 0 errors in 2305.7 s.** The cavity case now passes with
non-zero probes (the excitation fix); `nf2ff_dipole` needed the Rust `nf2ff` CLI
at `<repo>/openEMS/nf2ff/nf2ff`, which `scripts/ci/link_rust_openems.sh`
provides (native `searchBinary` concatenates PATH entries without a separator,
so a PATH lookup cannot match).

The absolute times are ~1.9x the earlier run on the previous worktree. The
restored tree lives on a slower volume and the dump-heavy cases are I/O bound;
the assertions, sample counts and values are unchanged, so this is a disk
effect, not a solver change.

## CI and record gates (RM-007, RM-008)

| Check | Command | Result |
| --- | --- | --- |
| Placeholder gate self-test | `python scripts/ci/check_placeholders.py --self-test` | `placeholder checker self-test passed` -- a seeded `todo!()` is reported, a file whose only marker is the allowed `unreachable!()` is not, and an allowlisted file is excused |
| Placeholder gate in CI | `.github/workflows/rust.yml` lines 58-60 (`--changed --base`, then `--changed` for a push) | green on every run since run 40580893146 |
| Register consistency | `python scripts/ci/check_migration_docs.py` | `migration record check passed`: closed vocabulary, snapshot counts, backlog header, coverage statuses |
| Session log | `REMEDIATION_PLAN.md` Section 12 and the `REMEDIATION_TASKS.md` progress-evidence table | one entry per session; every status change carries date, evidence path and command |

## Cylindrical path walk (RM-148)

| Check | Result |
| --- | --- |
| Ported | `fit_to_alpha_range` (`operator_cylinder.cpp:226-250`), the `SnapToMeshLine` azimuth fold (`:277-282`), the two `SnapLine2Mesh` seam remaps (`:307-317`), `find_path_cylindrical` (`:320-475`), and `line_plane_intersection`/`determinant3`/`invert3` (`tools/useful.cpp:272-328`) |
| Dispatch | `find_path` chooses the cylindrical walk from the mesh type, so the excitation curve branch and `calc_pec_curves` take it with no call-site change (native virtual call) |
| Decreasing azimuth | 90 deg -> 0 deg returns exactly the increasing path `(0,[3,0,3]), (1,[3,0,3]), (1,[3,1,3]), (1,[3,2,3]), (0,[3,3,3])`, because native swaps the endpoints (`:339-348`) |
| Span above pi | 90 deg -> 300 deg folds to -60 deg -> 90 deg (`:331-337`); the base walk then clamps -60 deg to alpha line 0 and yields `(1,[4,0,2])` |
| Seam crossing | closed 6-sector mesh, `(rho 2, 300 deg) -> (rho 5, 10 deg)`: `(1,[2,5,2]), (0,[2,6,2]), (0,[3,6,2]), (0,[4,6,2])`, including the closed-alpha remap `0 -> numLines[1]-2` (`:467-472`) |
| Native internals | both native binaries (`~/openems-exact` and the pinned v0.37.0) print `A path was leaving the alpha-direction mesh...`, `Intersection top: 3.6138,6.28319,2`, `Intersection bottom: 3.6138,0,2`, `Voltage excitations: 4 (3, 1, 0)` on the same input XML -- the port reproduces the split, the reused upper intersection on a closed azimuth and the 3 radial + 1 alpha distribution |
| Probe agreement | cylindrical seam probes differ from native by 4.7e-7 / 2.1e-7 / 2.2e-7 (Ex/Ey/Ez); further probes at (rho 2, 60 deg) and (rho 5, 60 deg) agree to 1e-6, a constant-rho seam curve to 1e-6, a Cartesian curve control to 1e-6 and a `Box` excitation of the same cell to 1e-7 |
| Regression | `openems-core` 250 + 2 tests; the Cartesian cavity curve gate reproduces 4.8e-5 / 9.2e-6 / 2.9e-5 on the peaks; `run_cylindrical_r0_check_wsl.sh` passes (4.2e-5) |

Not reproduced: the native verbose `FindPath` diagnostics beyond the
intersection error (semantics unaffected), and the unused `dist` out-parameter
of `LinePlaneIntersection`. `Operator_Cylinder::SnapBox2Mesh` (`:284-305`) is
still unported and belongs to RM-144.

## Metal curves are PEC (RM-150)

| Check | Result |
| --- | --- |
| Implementation | `calc_ec_operator` calls `calc_pec_curves`: METAL property curves are walked with `FindPath` (points evaluated in the operator mesh system with the primitive transform) and `VV`/`VI` are zeroed on every path edge, with the primitive marked used |
| Native parity | mirrors `Operator::CalcPEC_Curves` (`FDTD/operator.cpp:2064-2097`); only a `Curve` is walked (`ToCurve()` matches `Type == CURVE`), and the native `m_Nr_PEC` statistics counter has no Rust consumer |
| Test | `metal_curve_marks_the_path_as_pec`: the two path edges are exactly zero, the neighbouring edge keeps `VV = 1` and `VI > 0`, and the primitive is used |
| Regression | `openems-core` 245 + 2 tests; cavity curve gate unchanged (peaks 4.8e-5 / 9.2e-6 / 2.9e-5) |

## Curve and wire excitations (RM-149)

| Check | Result |
| --- | --- |
| `FindPath` port | native neighbour order and tie-breaking, `SnapLine2Mesh` (dual=false, full=true), `Point_Line_Distance` with the cylindrical chord metric, out-of-domain failure, closure loop |
| Curve branch | point evaluated in the operator mesh system with the primitive transform, path walked, `amp = GetWeightedExcitation * GetEdgeLength`, types 0 and 1 only, VV/VI zeroed for hard excite |
| Unit tests | 5: tie-breaking staircase (hand-derived), axis-aligned segment, out-of-domain, cylindrical metric (the inward first step pins the chord metric), end-to-end curve excitation |
| `openems-core` | 245 + 2 tests pass |
| Cavity differential | peaks 5.807516e-06 / 2.316531e-05 / 7.766571e-06 vs native 5.807240e-06 / 2.316510e-05 / 7.766348e-06 (4.8e-5 / 9.2e-6 / 2.9e-5); maximum sample difference 1.6e-4 / 4.5e-5 / 1.2e-4; **bit-identical** for all 6667 samples when the native timestep is pinned, which isolates the residual to the pre-existing `calc_timestep` summation-order difference |
| Regression | `Coax` `ut1`/`et`/`ht` and all `msl_port` probes are byte-identical before and after the change; `scripts/ci/run_curve_excitation_check_wsl.sh` gates the behaviour |
| Wire primitive | not walked: native `ToCurve()` matches `Type == CURVE` only, and the earlier wire fallback produced a 4.27e-5 probe where native is exactly zero; `wire_excitation_is_not_walked_as_a_curve` pins it |
| Not ported | the `Operator_Cylinder` overrides (azimuth fold, start/stop swap, alpha-seam split), tracked as RM-148; metal curves are not PEC yet (RM-150) |

## MATLAB C-ABI contracts (RM-094)

| Check | Result |
| --- | --- |
| Exported symbols | 34 `extern "C"` entry points (26 pre-existing + 8 added), identical to `nm -D`, pinned by `src/abi_inventory.rs` |
| Crate tests | 25 passed (3 inventory + 22 contract), `cargo fmt --check` and `clippy --all-targets` clean |
| Octave consumer | 54 checks through an `.oct` shim linked against both delivery libraries (Octave 11.1.0 has no `loadlibrary`) |
| Native citations | every expectation quotes the native file:line (face accessors `openems.cpp:810-846`, `SetCSX` ownership `:1163-1175`, setup codes `:1177-1234`, `SetBoundaryCond.m:51-71`, Python controller `openEMS.pyx:169-179/320-331`, deleted-object message `CSXCAD.pyx:118`) |

Deviations fixed: `Get_BC_Type`/`Get_PML_Size` now return the native `-1`
sentinels, `Set_BC_PML` forces the face type, the Reset default PML size is 8,
`SetupFDTD` reports the native codes 3 and 2 with messages, `SetCSX(NULL)` is a
clear instead of a null dereference, and `openems_free` drops the geometry.
Array orientation is asserted in both 1x6 and 6x1 column-major shapes.

Recorded deviations: a missing excitation aborts native `SetupFDTD` with code 3
while the core applies a default pulse (tracked as a follow-up on
`openEMS/rust/src/openems.rs`), and `set_over_sampling(0)` is clamped because
native zero divides by zero in processing.

## CI platform matrix and HDF5 feature (RM-026, RM-030, RM-120, RM-124)

`.github/workflows/rust.yml` run `40580893146`:

| Job | Result |
| --- | --- |
| Linux (workspace check, five numerical crates, policy gates) | green, 2m9s |
| macOS (workspace check + the same tests) | green, 2m59s |
| Windows (workspace check + tests, HDF5 from vcpkg) | green, 8m7s |
| FreeBSD (workspace check without `hyp2mat-rs`, fparser differential) | green, 2m49s |
| Linux HDF5 feature (`csxcad-core` + `openems-core`, six HDF5 reader tests) | green, 1m52s |
| fparser differential (macOS) | green, 54s |
| Reference (differential harness over `reference-data/`) | green, dispatched run `40580897904`, 4m8s |

The `hdf5` feature is unified across the workspace, so every job installs the
development files (apt, vcpkg, Homebrew, FreeBSD pkg); the HDF5 job also runs
`reads_native_discrete_material_hdf5_layout_and_properties`. FreeBSD excludes
`hyp2mat-rs` only because its `clipper2c-sys` backend has no FreeBSD target
(exception `E-004`); the solver, CSXCAD, CTB, GUI crates and the fparser
differential suite all run there. `RM-124` adds a nightly `cron` schedule to the
Reference workflow; the dispatch path is proven, the first scheduled artifact is
still pending.

## fparser optimizer coverage and decisions (RM-023..RM-025)

### Measured optimizer coverage (RM-023)

`fparser/rust/tests/run_differential.py` builds the pinned C++ parser
(`tests/original_reference.cpp`, CMake) and the Rust parser, runs both over the
same corpus and compares values (tolerance 1e-12, explicit non-finite and
float-boundary values), plus the callback-call counts that make the optimizer
observable.

| Corpus part | Rows | Optimizer-enabled |
| --- | --- | --- |
| checked-in cases (`differential_cases.tsv`) | 485 | 328 |
| generated operator matrix (14 operators x 31 values x 2) | 15,180 | 7,590 |
| generated builtin matrix | 2,920 | 1,460 |
| generated nested builtins | 26,245 | 13,123 |
| nested optimizer regressions | 126 | 126 |
| zero/error rewrites | 81 | 81 |
| signed `exp`/`log` rewrites | 48 | 48 |
| negative `sqrt`/`log` rewrites | 54 | 54 |
| signed nested composition | 84 | 84 |
| **total** | **45,223** | **22,894** |

Result: **45,221 expressions and 45,196 callback-count checks compared with zero
mismatches** under the recorded tolerances.

Residual risk (bounded): the Rust optimizer is a targeted port (constant
folding, legacy math lowering, function sharing and the observable nested
rewrites such as `csc(asin(x))`, `log(csc(acos(x)))`, `cbrt(sqrt(x))`), not a
rule-for-rule port of the 262 generated optimizer rules. A rule whose effect is
not observable in a value or in a callback count is not individually asserted;
the 22,894 optimizer-enabled cases are the mitigation, and every observed
difference is a defect, not tolerance noise.

### Decisions (RM-024, RM-025)

| Task | Decision |
| --- | --- |
| RM-024 optional numeric backends | `ADR 0006` keeps `f64` only; the omitted variants (`float`, `long double`, long integer, MPFR/GMP) are recorded as exception `E-001` with the impact and the compatibility path |
| RM-025 C++ API/FFI surface | `ADR 0008`: the Rust crates are canonical, there is no C++ source/binary-compatible wrapper, external surfaces are the CLI binaries, the Python packages, the MATLAB/Octave CLI plus a narrow reviewed C ABI, and the CSXCAD XML format; a C ABI is allowed only as documented foreign-runtime glue, and system HDF5 remains the only library FFI (`E-002`) |

## Python packages under the native names (RM-013)

| Check | Result |
| --- | --- |
| `CSXCAD/rust-py` packaging | new `pyproject.toml`: `python-source = "python"`, `module-name = "csxcad_py"`, `python-packages = ["CSXCAD"]`; the wheel ships the compiled `csxcad_py` extension **and** the pure-Python `CSXCAD` package (native layout `CSXCAD.CSXCAD`, `CSXCAD.CSProperties`, `CSXCAD.CSPrimitives`, `CSXCAD.CSRectGrid`, `CSXCAD.CSTransform`, `CSXCAD.Utilities`) |
| `openEMS/rust-py` packaging | distribution name changed from `openems-py` to the native `openEMS`, so `importlib.metadata.version("openEMS")` resolves and `openEMS.__version__` is `0.1.0` instead of the fallback `0.0.0` |
| Installed import | `cd /tmp && env -u PYTHONPATH python -c "from CSXCAD import ContinuousStructure; from openEMS import openEMS"` -> `CSXCAD 0.1.0`, `openEMS 0.1.0`, `ContinuousStructure().GetGrid()` -> `CSRectGrid`, solver class `openEMS.openEMS.openEMS` |
| CI gate | `scripts/ci/build_rust_python_wsl.sh` now performs that import from `/tmp` with `PYTHONPATH` unset after `maturin develop`, so a wheel that loses the package fails the build |
| Regression | native Python suites still pass against the installed packages: 298 openEMS + 150 CSXCAD |

A stale `site-packages/csxcad_py` copy left by an earlier non-package build had
to be removed once; the editable install now points at the repository source.
The repository root is not safe as a working directory for the import check
because the `CSXCAD/` source directory shadows the installed package (the native
tree has the same property); the check runs from `/tmp`.

## CSXCAD depth: native XML corpus and differential harness (RM-027..RM-036)

### Corpus

`CSXCAD/rust/tests/native_gen/run_native_generator.sh` copies the pinned native
`CSXCAD/` and `openEMS/` (never the repository copies), builds them, and writes
fixtures back into the repository:

| Artefact | Content |
| --- | --- |
| `tests/fixtures/xml/` | 11 documents written by native `ContinuousStructure::Write2XML` + `manifest.txt` (property types, primitive types, transforms, parameters, cylindrical coordinates, background/grid, openEMS wrapper, DiscMaterial) |
| `tests/fixtures/native/` | 11 model reports produced by a **native re-read** (`ReadFromXML`, `read_back = 1`) |
| `tests/fixtures/mesh/` | 22 STL/PLY files (native test meshes, VTK-written ASCII/binary STL, quad PLY, multi-solid, malformed) + VTK-derived expectations |

Two complete regenerations produced the identical fixture hash
`58726f26e30b24465c30e7082c8edd687370446e5d3e938a682c3a732235e17d`, so the corpus is
reproducible rather than hand-written.

### Results

| Area | Evidence |
| --- | --- |
| XML dispatch and round trip (RM-028) | manifest/disk agreement, strict and compatibility parse, native -> Rust -> Rust -> Rust model equality, byte-stable second write, openEMS wrapper extraction, native transform element names |
| Differential model harness (RM-029) | counts and types, grid, background, parameters (native `IncreaseStep` walks), property fields, primitive priority/coordinate system/bounds/dimension, transform matrices, containment/priority queries, object area, native `isGeometryValid` |
| Expression integration (RM-027) | parameter/coordinate/weight/transform expressions through bounding boxes and containment; native error codes 1, 2, 3, 4, `100 + fparser code`, `-1`; strict error vs native warn+skip for a malformed transform |
| Transform/parameter parity (RM-034) | native `tscenario` matrices (pre/post multiply, `Rotate_Origin`, degree mode, `Matrix`+`Scale3`, invert), extra-argument truncation, zero axis, singular inverse, sweep/`set_linear_range`/zero-step termination |
| Mesh corpus (RM-035) | exact point/face order and winding, quad arity, multi-solid merging, XML round trip, malformed rejection; empty meshes rejected like native |
| Performance baseline (RM-036) | 158,337-byte document: release serialize 3.03 ms (49.8 MB/s), parse 4.04 ms (37.3 MB/s), bounds 1.50 microseconds/primitive, 100 containment queries 183 ms; debug 10.20/16.03 ms |
| Tests | `cargo test`: **194 passed** (157 lib + 37 integration); `cargo test --features hdf5`: **200 passed** (163 lib) |

Porting defects fixed by this wave: native transform element names on write,
native extra-argument truncation, and the `Box` update-error path (evaluate all
`P1` components, short-circuit `P2` only when `P1` fails).

The native `DispersiveMaterial` tag cannot be dispatched because native never
writes it; `11_disc_material` reports `read_back = 0` because native cannot
reload a `DiscMaterial` without its HDF5 file. Both are recorded in the reports
and asserted in the tests.

## hyp2mat parity (RM-107..RM-111)

| Check | Result |
| --- | --- |
| Fixtures (RM-107) | 9 `.hyp` files: 3 native EAGLE examples, 6 grammar-derived synthetic files (planes/clearances, pours/voids, arcs, vias, rotated/oval/oblong pads, cutout, multi-layer, flood, metric/english/weight); SHA-256 manifest + provenance README |
| Polygon operations (RM-108) | stateful native `Polygon` with a Rust port of Clipper 1's offset builder; expectations from a native oracle built against `lib/polygon.cc`, compared as exact grid-unit vertex sets |
| CSXCAD output (RM-109) | `-f csxcad` reproduces the native MATLAB writer (non-polygon lines byte-identical; geometry exact for 7/9, <= one 10 um step on the two arc fixtures; copper area <= 1.7e-3 relative). `tests/native/run_native_read_check.sh`: pinned native `libCSXCAD` reads all 9 Rust XML documents and its model dump is **identical** to the Rust dump (255 lines: counts, types, names, material values, grid, delta unit, background, priorities, owners) |
| QucsStudio and PDF (RM-110) | properties exact, items within the same one-grid-step bound, identical stderr multiset; PDF renders under Ghostscript 10.06 with 3/3/3/3/4/3/3/5/3 pages (composite + one page per metal layer) |
| CLI (RM-111) | full native option set, stdin/stdout, `--help`/`--version`, exit codes and messages, binary installed as `hyp2mat`; `-v` board/layer summary byte-identical to native `std::cerr` for 9/9 fixtures; five output variants per fixture are deterministic (45/45 identical SHA-256); 23 CLI integration tests |
| Tests | `cargo test`: **114 passed** (77 lib + 23 CLI + 14 fixture); `cargo fmt --check` and `cargo clippy --all-targets` clean |

Preserved native quirks: `{UNITS=METRIC}` means centimetres, imperial copper
weight thickness is 1000x (native defect), device `VAL=` is always a string, a
deprecated `PAD` yields a zero-size pad, the plane-mask filter uses the target
net name, a syntax error exits 0, and `-f pdf` without `-o` prints
`pdf output file missing` and writes nothing. The additive `--csxcad-xml`
extension is the only new output path; `-f csxcad` keeps the native MATLAB
script so `matlab/ImportHyperLynx.m` still works.

Accepted deviation: the two arc fixtures resolve one shallow polygon
intersection one 10 um grid step apart (Clipper2 versus Clipper 1 integer
rounding). The bound is 1.5 grid steps and is asserted explicitly; it is
recorded in `REFERENCE_TOLERANCES.md` and awaits owner re-approval.

## Regression CI (RM-123)

`.github/workflows/reference.yml` runs on every push/PR that touches Rust,
Python, `scripts/ci` or the reference captures:

| Step | Command | Result |
| --- | --- | --- |
| Numerical core | `cargo test -p fparser-rs -p csxcad-core -p openems-core -p ctb-rs -p hyp2mat-rs` and `cargo test -p openems-core --features hdf5` | PASS |
| Python suites | `bash scripts/ci/run_rust_python_tests_wsl.sh` | PASS |
| Differential harness | `bash scripts/ci/run_reference_harness_wsl.sh` (4/4 cases) | PASS |

GitHub Actions evidence on `mberkanbicer-rust-migration-audit`: runs
40394042360, 40398852196, 40409688197, 40422519177, 40482929043 and
40495994980 all finished `success` (3m34s..5m45s); the last one ran commit
`33802a4`. The runner installs `libhdf5-dev`, `pkg-config`, `python3-venv`,
`numpy`, `scipy`, `h5py` and `matplotlib`, then builds the maturin extensions.

## GUI PNG capture and visual QA (RM-105, RM-106)

| Check | Measured | Verdict |
| --- | --- | --- |
| PNG writer | a 2x1 RGBA buffer decodes back byte-identical; a wrong buffer length is rejected | PASS |
| Offscreen capture | 64x48 render of an orange box: 3072 RGBA pixels, >100 non-background pixels, `export_image` writes a 64x48 PNG that decodes to the same content | PASS |
| Full UI frame | 1280x800 frame through the real wgpu pipelines and egui widgets: `audits/gui-screenshot.png` (251592 bytes, 1280x800, >50 distinct colours). The layout shows the tree with `Material::substrate`, `Box - ID: 1` and the selected `Sphere - ID: 2`, the property editor (name, visibility, coordinates, colors, isotropic, Epsilon/Mue/Kappa/Sigma), the primitive editor (priority, center, radius, delete), the mesh/parameter editor and the 3D viewport with the sphere and box | PASS |
| Defects found by the artifact | duplicate `ScrollArea` ID (egui warning), missing arrow/bulb glyphs (empty boxes) and a selected primitive hidden by the tree's expansion state; all fixed | PASS |

The frame is rendered offscreen because WSLg cannot present a frame in this
environment (`Io error: Broken pipe`). Seven interactive items (real-display
presentation, keyboard-focus edge case, dialogs, mouse interaction, camera
controls, native side-by-side parity, platform matrix) remain open in
`audits/gui-qa.md`; RM-106 therefore stays `Implemented`.

## GUI project I/O, undo/redo and exports (RM-102..RM-104)

Verified headlessly; the interactive checklist is RM-106.

| Check | Measured | Verdict |
| --- | --- | --- |
| Undo/redo | add property -> rename -> undo -> undo restores `""` and then removes the property; redo replays both; a new edit clears the redo stack; primitive, grid-line and parameter edits undo in reverse order; the history stops at 100 steps | PASS |
| Bare CSXCAD round trip | read -> edit -> render -> re-read equals the edited structure; a single XML declaration | PASS |
| openEMS wrapper round trip | `<FDTD NumberOfTimesteps="1000" EndCriteria="1e-5"/>`, `<BoundaryCond .../>` and `<Excitation Type="0" f0="1e9"/>` survive a save; exactly one `<ContinuousStructure>` element | PASS |
| Save / Save As | Save writes the loaded path and clears the modified flag; Save As adopts the new path and a following Save writes it | PASS |
| CLI | `appcsxcad --disableEdit --export-polydata-vtk=/tmp/appexp <project.xml>` loads the project, prints the native export lines and writes `ground.vtp` (2252 bytes, `NumberOfPolys="12"`, `NumberOfLines="12"`); a missing project reports an error | PASS |
| Exports | per-property `.vtp` (`NumberOfPolys="12"`, scaled by the 1 mm delta unit), binary `.stl` (12 triangles, 84 + 50*12 bytes, scaled), ASCII `.ply` (36 vertices, 12 faces), POV-Ray `mesh2` with two `vertex_vectors` blocks and the fill colors, X3D with two `IndexedFaceSet` elements | PASS |
| Settings | the persisted window size round-trips and clamps to 320x240 .. 16384 | PASS |

### Migration decisions

- Save preserves the openEMS wrapper. Native `QCSXCAD::Write2XML` writes only
  the `ContinuousStructure` element, so a save after opening a solver project
  drops every openEMS setting. The port substitutes the regenerated structure
  into the original document instead; the decision is recorded in
  `audits/gui.md`.
- Save As adopts the new path. Native's export dialog leaves `m_filename`
  unchanged, so a following Save writes the previous file; the port updates it.
- New properties start without a fill color (native assigns a random color at
  construction) so documents and exports are reproducible.
- Property file names fall back to `property_<index>` and replace path
  separators, so an export can never leave its directory.
- File dialogs are in-app path windows instead of `QFileDialog`; the file
  operations themselves are the same.
- `--disableEdit` is implemented; `--RenderDiscMaterial` records the render
  flag but no longer toggles the edit flag (confirmed native defect). Discrete
  material rendering itself is tracked as RM-147.

## GUI editing model (RM-098..RM-101)

The editing wave is verified headlessly; the interactive checklist is RM-106.

| Check | Measured | Verdict |
| --- | --- | --- |
| Tree labels and grouping | `tree_rows` emits `Material::substrate` and `Box - ID: 1` in model order, hides primitives of collapsed properties and carries the property visibility/color | PASS |
| Property edits | Name, visibility, fill/edge color, coordinate system, material (isotropic + 3 components of Epsilon/Mue/Kappa/Sigma), excitation (type, number, enabled, frequency, delay, per-component excitation and propagation terms), probe (number, type, normal, weight, start/stop, oversampling, FD samples), dump (type, mode, file type, multi-grid level, sub-sampling, oversampling, FD samples, SAR method) and resolution factor survive `to_xml_string` -> `from_xml_str`; mismatched edits return an error | PASS |
| Primitive edits | Add/edit/delete of a box (bounds `[-1,1] x [-2,2] x [-3,3]`, priority 4) survives a reload; all six native creatable types build; a frame with twelve primitive shapes renders without panic | PASS |
| Grid and parameter edits | Lines, delta unit and resolution increase survive a reload and every axis compares line by line; constant and linear parameters round-trip name, value, `(min, max, step)` and the sweep flag; removing a parameter shifts the indices | PASS |
| Editor frames | `egui::Context::run_ui` renders the tree, property, primitive and mesh editors over a document with all six property types and every renderable shape | PASS |

### Defect found: duplicated dump-box oversampling

Native `CSPropProbeBox` owns the single `m_OverSampling` field and
`CSPropDumpBox` inherits it. The Rust model had a second `oversampling` field
on `DumpBoxProperties`; both writers set the same `OverSampling` attribute, so
the dump value silently replaced the probe value in every written file, and
the FD dump path read the dump copy while the Python setter wrote the probe
copy. The dump copy is removed; dump boxes now read the probe field, matching
native.

## GUI renderer and application launch (RM-015, RM-097)

The GUI wave has no numerical reference yet; the evidence is unit-test and
launch based:

| Check | Measured | Verdict |
| --- | --- | --- |
| `qcsxcad-core::tessellate` geometry | 11 tests: box bounds and 12 triangles, degenerate plane, cylinder axis/radius, sphere radius, spherical shell radii, extruded polygon elevation/length, rotational polygon revolution, cylindrical wedge bounds, polyhedron triangulation, wire tube surfaces, transform + property colors | PASS |
| `qcsxcad-egui` camera | center projects to the NDC origin; fitted bounds stay inside the clip volume for the perspective and orthographic cameras | PASS |
| `appcsxcad --version` / `--help` | `AppCSXCAD 0.1.0` / usage text, exit 0 | PASS |
| headless graphical launch | window creation, egui buffer updates and the 3D pipelines run without wgpu validation errors; the WSLg compositor cannot present a frame (`Io error: Broken pipe`), so the interactive launch awaits the RM-106 checklist | LIMITED |

The tessellation mirrors the native `VTKPrimitives` sources listed in
`audits/gui.md`; visual parity against native screenshots is still pending
(RM-106). Four launch blockers found here were fixed: argv[0] was opened as
the input file, egui had no bundled fonts, `update_buffers` was never called
and the egui pipeline declared no depth format while the pass carried a depth
attachment.

## Cylindrical SAR (RM-143)

`scripts/ci/run_cylindrical_sar_check_wsl.sh` runs a lossy muscle-like shell
(eps_r = 80, kappa = 1 S/m, density 1000 kg/m^3, 16 sectors, rho = 0 axis) with
a raw SAR dump (`DumpType` 29) and a 1 g result dump (`DumpType` 21), driven by
the same `input.xml` through the Rust and native solvers:

| Check | Measured | Bound | Verdict |
| --- | --- | --- | --- |
| `/Mesh` layout (`rho`,`alpha`,`z`, `mesh_type=1`, `mesh_scaling=1e-3`) | identical | - | PASS |
| `/CellData/Volume` vs native and vs `dA/2 (r2^2 - r1^2) dz` | 0.0 difference, 3.5e-8 vs analytic | 1e-6 | PASS |
| `/CellData/Density`, `/CellData/Conductivity` | 0.0 difference | 1e-6 | PASS |
| raw E-field DFT (`f0`) vs native | 1.195e-3 | 1e-2 | PASS |
| 1 g SAR peak vs native | +0.32 % | 1 % | PASS |
| 1 g SAR per cell vs native | 6.4e-1 of the peak (1534 of 1936 cells above 1 %) | not gated | FAIL (RM-145) |
| probe cadence / stop time | 251 vs 1001 samples | not gated | FAIL (RM-146) |

Two engine bugs were found by this case and fixed with unit coverage:

* `AverageMatQuarterCell` weights the quarter cells by `GetNodeArea`, not by the
  rho-face `GetEdgeArea`; the latter applies the primary rho factor and
  vanishes on the `rho = 0` axis, so every axis E_rho cell fell back to the
  background material. Dielectric cylindrical meshes therefore took a vacuum
  timestep (9.089e-13 s instead of the native 8.12933e-12 s, a factor
  `sqrt(eps_r)`) and used wrong EC values on the rho = 0 sheet. The new test
  `cylindrical_r0_timestep_includes_the_dielectric` pins the native value.
* Closed-azimuth seam/padding samples must wrap into `[alpha0, alpha0 + 2*pi)`
  like native `GetYeeCoords`, otherwise those cells resolve the background.

The remaining per-cell 1 g differences come from the mass-averaging cube search
(RM-145) and the stop-time difference from the end-criteria evaluation (RM-146);
both are reported by the check and tracked as their own tasks.

## Cylindrical field dumps (RM-138)

`scripts/ci/run_cylindrical_dump_check_wsl.sh` mirrors the plain half of the
native `python/Tests/Cylindrical_Cavity.py` (closed PEC pillbox with the
`rho = 0` axis, E-field FD dump of `f_010` over the full ring at mid-height)
and runs the native solver on the same `input.xml`:

| Check | Measured | Bound | Verdict |
| --- | --- | --- | --- |
| `/Mesh` layout (`rho`,`alpha`,`z`, `mesh_type=1`, `mesh_scaling=1e-3`) | identical dataset shapes (21, 24, 1) | - | PASS |
| `/Mesh` values | 0.000e+00 relative | 1e-9 | PASS |
| `/FieldData/FD/f0` E-field DFT vs native | 5.221e-6 relative | 1e-2 | PASS |
| TM010 radial Ez profile vs `J0(x_01 r / R)` | 0.0003 | 0.03 (native test bound) | PASS |

The azimuth is written in radians (unscaled), rho/z in metres, exactly like
the native `HDF5_File_Writer::WriteRectMesh`. Two collateral unit bugs were
found by the case and fixed: the processing metadata used to scale azimuth
coordinates by the grid delta (which snapped probes and dump boxes to wrong
azimuth lines) and the dump files recorded `mesh_scaling = 1` instead of the
grid delta. The cylindrical snapping now ports `FitToAlphaRange`, the
cylindrical `SnapBox2Mesh` recentring and the `fullMesh = false` semantics of
`Processing::DefineStartStopCoord`.

## Cylindrical rho = 0 axis (RM-137)

`scripts/ci/run_cylindrical_r0_check_wsl.sh` runs a closed PEC pillbox
(R = 50 mm, h = 30 mm, dr = dz = 2.5 mm, 24 azimuthal sectors) on a mesh that
includes the `rho = 0` axis, mirroring the plain part of the native
`python/Tests/Cylindrical_Cavity.py`, and additionally runs the native solver
on the very same `input.xml`:

| Check | Measured | Bound | Verdict |
| --- | --- | --- | --- |
| TM010 resonance vs `x_01 c / (2 pi R)` | 2.2940 GHz vs 2.2949 GHz (-0.04 %) | 1 % | PASS |
| TM110 resonance vs `x_11 c / (2 pi R)` | 3.6500 GHz vs 3.6565 GHz (-0.18 %) | 1 % | PASS |
| probe `et` (Ez, r = 25 mm, alpha = pi/4) vs native | 4.162e-5 relative | 1e-2 | PASS |
| native and Rust mode frequencies | identical (2.2940 / 3.6500 GHz) | - | PASS |

The case is stable for the full 40000 steps only with native's conservative
`Rennings_1` step: native `Operator_Cylinder::CalcTimestep` forces it whenever
`discLines[0][0] == 0`, while `Rennings_2` produces a 3.2x larger step that
diverges within a few dozen timesteps. Two collateral compatibility gaps were
fixed on the way: `et`/`ht` must be written before `SetupProcessing` (a probe
reusing those names truncates the file, as native does) and a non-positive
`EndCriteria` must keep the native 1e-6 default.

## Cylindrical operator (RM-134)

Command: `scripts/ci/run_octave_testsuite_wsl.sh` (native testsuite, unchanged).

| Case | Result | Reference evidence |
| --- | --- | --- |
| `combinedtests/coax_cylindrical` | PASS | beta = k0 within 0.20 % (limit 1 %), radial voltage profile within 0.013 % of `log(r_p/r_i)/log(r_o/r_i)` (limit 1 %), rotational symmetry 7.6e-17 (limit 1e-9) |
| full suite | 10 passed / 0 failed / 0 errors in 333.8 s | all ten native cases, including the previously deferred cylindrical case |

Rust unit coverage: `cylindrical_full_turn_is_accepted_and_padded`,
`cylindrical_metric_uses_rho_and_annulus_areas`,
`cylindrical_open_alpha_is_not_padded`,
`cylindrical_negative_rho_and_open_axis_are_rejected`, plus the seam-copy
assertions in `extensions::tests_cylinder`.

Not yet covered and therefore open: a mesh that includes the `rho = 0` axis
(rejected explicitly, RM-137) and cylindrical field dumps with the native
`/Mesh/{rho,alpha,z}` layout (RM-138).

## Direct SAR result dumps (RM-136)

Command: `scripts/ci/run_sar_dump_check_wsl.sh` (one Octave run with a
`DumpType` 29 raw dump, a `DumpType` 20 local result and a `DumpType` 21 1 g
result on the same lossy box).

| Check | Result |
| --- | --- |
| raw + `sar_calc` vs `sigma|E|^2/(2 rho)` | peak 6.509386e-22 W/kg, 7.8e-8 relative |
| direct type 20 vs raw + `sar_calc` peak | 6.5e-9 relative |
| homogeneous interior (uniform conductivity) | 0.0 (bit-identical) |
| whole block including the material boundary | 6.2e-3 relative, the native J-field vs cell-conductivity distinction (edge kappa is averaged over quarter cells that lie partly outside the box) |
| 1 g averaged direct dump | finite maxSAR 1.531e-22 W/kg with a positive mass attribute |

Rust unit coverage: `sar_hdf5::tests::direct_result_dump_matches_the_local_sar_formula`
(0.5*|E|*|J|/rho = 1 W/kg) and the existing `sar` averaging tests.

## Differential reference harness (RM-117)

Command: `scripts/ci/run_reference_harness_wsl.sh [--case <name>]`. The harness
runs the unmodified pinned Python sources against the Rust core, keeps the
solver output (including `input.xml`) and compares the derived quantities with
the native captures in `docs/migration/reference-data/`. Bounds and their
justification are in `REFERENCE_TOLERANCES.md`.

| Case | Check | Measured | Verdict |
| --- | --- | --- | --- |
| coax 3-D (715 k cells) | `Z_ref` real | 7.5e-5 relative | PASS |
| coax 3-D | `S21` | 1.9e-4 dB | PASS |
| coax 3-D | `S11` worst in band | -50.83 dB vs -50.88 dB | PASS |
| conducting sheet (resistive film) | `|T|` | 0.036 dB vs native | PASS |
| conducting sheet (thin copper) | `|T|` | 0.036 dB vs native | PASS |
| conducting sheet (thick copper) | `|T|` | 0.073 dB vs native | PASS |
| conducting sheet | phase | 0.178-0.199 deg vs native | PASS |
| fieldprobes | all probe/dump checks | probes 1.5e-5, Ef/Hf 1.2e-5, H TD 3e-5 | PASS |
| msl-notchfilter | `et`/`ht`, `port_ut_*`, `port_it_2*` | 1.4e-8 .. 6.0e-6 | PASS |
| msl-notchfilter | `port_it_1A/1B` (excited port) | 1.5e-6 .. 1.9e-6 | PASS |

The harness found and localised three real defects. The D/B one is fixed:

* native `m_epsR`/`m_mueR` store the **absolute** permittivity/permeability
  (`Operator::DumpMaterial2File` divides them by `EPS0`/`MUE0`), so the D and B
  dumps are `eps0*eps_r*E` and `mue0*mue_r*H`. The Rust conversion multiplied by
  the relative values only, which the FieldProbes source test caught as a
  `1/eps0` relative error. Fixed in `processing.rs`, with the unit test updated
  to the absolute values.

The same run showed that the `et`/`ht` excitation waveforms were missing from
the solver output; they are now written before the time loop and match the
native MSL reference to 2.1e-6. The MSL reference then exposes one more gap:
the Python `AddMSLPort` current probes of the *excited* port are all zero
(RM-141), while the voltage probes and port-2 currents match.

The FD-dump gap is fixed: the DFT interval follows native
`min(global Nyquist, freq)`, probes default to FD oversampling 1, FD VTK dumps
write `.vtr` rectilinear grids with the real mesh, and cropped dumps apply
`SnapMethod = 1`. `fieldprobes` now passes every harness check.

The conducting-sheet gap is closed. The root cause was the magnetic boundary
condition: Rust `apply_magnetic_bc` cleared only the two tangential current
components, while native `Operator::ApplyMagneticBC` also clears the normal one
on a low PMC face, the tangential ones one line inside a high PMC face
(`numLines - 2`), and the outermost line of every axis (outside the iterated
domain). In the 1 mm PEC/PMC parallel-plate channel the surviving normal H
destroyed the single-row TEM mode: the pulse propagated at 0.69 c with a 1.42x
amplitude. With the native clearing rules the incident probe matches the
reference exactly (amplitude ratio 1.00000, 0.0 ps delay at z = 20..120 mm,
v = c) and all three sheet cases pass the differential bounds.

The excited-port gap is closed as well. Native `ProcessCurrent` treats a
current probe as a closed surface: every tangential axis requested with zero
extent is grown by one dual line. Rust snapped the box but kept the line flat,
so the two opposite faces of the probe were evaluated on the same line and the
+y/-y terms cancelled exactly (a hard zero where native reads 9.6e-8). With the
expansion `port_it_1A/1B` match to 1.5e-6/1.9e-6. All four reference cases pass,
which closes RM-118; the remaining step (RM-119) is owner approval of the
recorded bounds.

## nf2ff native round-trip and the DFT weight (RM-076, 2026-10-29)

Command: `scripts/ci` build of `nf2ff-cli` plus the native `nf2ff` from the
pinned v0.37.0 build, both run on the time-domain dumps that the Rust solver
wrote for `combinedtests/nf2ff_dipole`.

The native reader rejected the dump before the `uint8` flag fix
(`dual_mesh`, `legacy_fmt` are `H5T_NATIVE_UCHAR` in
`HDF5_File_Writer`). After the fix both runs produce a result file with the
same layout:

| Dataset | native peak | Rust peak | max relative difference |
| --- | --- | --- | --- |
| `nf2ff/E_phi/FD/f0_real` | 1.2890e-17 | 1.2890e-17 | 4.97e-6 |
| `nf2ff/E_phi/FD/f0_imag` | 7.7707e-18 | 7.7707e-18 | 1.57e-5 |
| `nf2ff/E_theta/FD/f0_real` | 4.3114e-16 | 4.3114e-16 | 4.62e-6 |
| `nf2ff/E_theta/FD/f0_imag` | 1.5597e-15 | 1.5597e-15 | 1.67e-7 |
| `nf2ff/P_rad/FD/f0` | 3.4747e-33 | 3.4747e-33 | 8.73e-7 |

Datasets are `f8`, the `Frequency` attribute is `f4` and the mesh datasets are
`f4`, matching native. The factor that had made the Rust field `1.08e10` too
small was the DFT weight: native `HDF5_File_Reader::CalcFDVectorData`
multiplies the sum by `2 * time_diff` (`tools/hdf5_file_reader.cpp:938-945`),
with `time_diff` the last recorded sample interval. The dump interval is
`4.6188022e-11 s` and `1 / (2 * 4.6188022e-11) = 1.0825e10`.
`time_domain_dft_applies_the_native_trapezoidal_weight` pins the factor with the
exact three-sample sequence `1, 0, -1`.

## Lossy medium (RM-054, 2026-10-29)

The operator dump fixture (`scripts/ci/run_operator_dump_check_wsl.sh`) now
uses `BackgroundMaterial Epsilon="4" Kappa="0.05" Sigma="0.01"`, so `EC_G`
(electric loss) and `EC_R` (magnetic loss) are both compared node by node
against the native `--debug-operator` dump:

| Coefficient | peak | max relative difference |
| --- | --- | --- |
| `vv` | 0.994577 | 9.8e-15 |
| `vi` | 108.458 | 4.3e-13 |
| `ii` | 1 | 5.96e-8 |
| `iv` | 0.00306506 | 4.8e-15 |

A parallel-plate TEM fixture (PEC plates, PMC walls, `Kappa=0.05`, 8 GHz,
probes 40 mm apart) attenuates, but the measured `alpha` is 8.7-9.5 Np/m against
the exact 6.65 Np/m; the lossless control still shows a 4% amplitude residue
from the finite PML, so the fixture is not yet tight enough to carry the 3%
analytic bound. The earlier attempt in the register used `Sigma`, the magnetic
conductivity, whose low-loss attenuation is ~6.6e-5 Np/m over the same path,
which is why it showed no loss. `RM-054` therefore stays `Implemented` with the
coefficient half verified.

## Var3 default and the Debye identity (RM-151, 2026-10-29)

Native `Operator::Operator()` sets `m_TimeStepVar = 3` (`operator.cpp:57`); the
port now does the same in `OperatorBaseImpl::new()`.
`var1_and_var3_match_the_uniform_mesh_analytic_values` asserts the default. The
Debye test now asserts the stored `v_relax_ADE`/`v_drive_ADE` values are the
correctly rounded f32 analytic coefficients (bit-exact equality) instead of
checking the exact identity `2 d / (1 - a) = delta_eps`, which the native
`FDTD_FLOAT` storage limits to a few 1e-7 at Var3. `openems-core --features
hdf5`: 266 + 2 tests pass.

## Native differential: lossy guide and UPML (RM-043, RM-054, 2026-10-29)

Two dedicated gates now run the same XML through the pinned native binary and
the Rust CLI and compare the E-field probe traces. Both use the approved 1 %
probe bound.

`scripts/ci/run_lossy_medium_check_wsl.sh` - parallel-plate TEM guide (PEC
plates in z, PMC walls in y, PML in x), 1 mm cells, `Kappa = 0.05 S/m`
everywhere, 8 GHz Gaussian, probes at x = 60 mm and 100 mm, 200 steps:

| Probe | max relative difference | native peak |
| --- | --- | --- |
| x = 60 mm | 7.5e-6 | 0.6240 |
| x = 100 mm | 1.1e-5 | 0.4244 |

Native probe ratio `p2/p1 = 0.6802`, i.e. the loss attenuates, and the port
reproduces it. The analytic `exp(-alpha d)` from the exact lossy-medium formula
is 0.7665, so the 11 % gap is a property of the native discretisation, not a
port difference; the native comparison is therefore the acceptance and no
analytic bound is used.

`scripts/ci/run_upml_reflection_check_wsl.sh` - 41x21x21 at 1 mm, eight-cell
UPML on all six faces, hard E_z 6 GHz Gaussian at the centre, probes at the
centre and 6 mm off-centre, 900 steps:

| Probe | max relative difference | absorbed tail |
| --- | --- | --- |
| centre | 6.0e-8 | 8.9e-8 native, 7.6e-8 Rust (-141 / -142 dB) |
| 6 mm | 1.0e-8 | - |

The library test `upml_absorbs_a_gaussian_pulse` reports -117 dB for the same
setup, consistent with the differential tail.
