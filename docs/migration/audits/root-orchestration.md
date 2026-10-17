# Root Build, CI, and Packaging Audit

**Status:** Root orchestration source audit complete. No build or packaging
script was changed. The WSL baseline build and test results are recorded in
`../VALIDATION.md`.

## Build graph and options

The root `CMakeLists.txt` uses `ExternalProject_Add` in dependency order:
`fparser -> CSXCAD -> openEMS`; when `BUILD_APPCSXCAD` is enabled, it also
builds `CSXCAD -> QCSXCAD -> AppCSXCAD`. The install prefix and dependent
`FPARSER_ROOT_DIR`/`CSXCAD_ROOT_DIR` values are passed down to subprojects.
GUI builds default on.

`update_openEMS.sh` wraps the root CMake build and offers optional hyp2mat,
CTB, Python bindings, GUI disablement, TinyXML-from-source, dependency-check
and job-count controls. It writes timestamped logs, builds hyp2mat and installs
CTB after the core project, and builds the Python extensions after native
installation. `scripts/build_python.sh` supports automatic, explicit, and
disabled virtual-environment modes plus an offline mode. On macOS, the wrapper
enables the pinned TinyXML source build by default because Homebrew no longer
provides TinyXML. `scripts/build_tinyxml.sh` verifies SHA-256 digests for the
downloaded source and patches before building.

`scripts/install_deps.sh` supports apt, dnf, apk, pacman, Homebrew, and FreeBSD
pkg. It has optional dependency sets for GUI, Python, and Octave/CTB; Alpine
forces GUI off because its VTK package lacks Qt support. Arch/Manjaro is
explicitly best-effort. The dependency checker does not model the optional
hyp2mat build's additional autotools/PDF dependencies.

`scripts/make_tarball.sh` assembles a source archive from the root and each
submodule's committed `HEAD`; it is separate from the normal CMake install.
In `doc-src/`, the CSXCAD/openEMS changelog pages link to their submodule
`CHANGELOG.md` files, and the generated Octave API pages are produced from
M-file help text by `generate_octave_docs.py`; edits belong in the upstream
source, not in generated or linked copies.

## CI and platform coverage

`.github/workflows/ci.yml` exercises:

- Linux containers for CentOS 7, Ubuntu 14.04, Debian oldstable/latest,
  Ubuntu 22.04/24.04/latest, Fedora latest, AlmaLinux 8/9, and Alpine without
  GUI. The two EOL systems have inline dependency/bootstrap steps; other Linux
  jobs use `install_deps.sh`.
- macOS latest on ARM and FreeBSD 14.2 x86-64.
- Windows latest with MSVC and clang-cl, building the C++ submodules directly
  with Ninja/vcpkg. The Windows job does not run the Matlab/Octave or Python
  smoketests.

Linux and macOS jobs build Python bindings with virtual environments disabled
and enabled, and run Octave/Python smoke tests. FreeBSD tests Octave and Python
in the workflow. Alpine is explicitly headless. All checkout paths request
full Git history and recursive submodules because the CMake version logic uses
`git describe --tags`.

## Confirmed source-level compatibility findings

1. **The Python `site` venv option is not passed through.** In
   `scripts/build_python.sh`, `create_python_venv` initializes `pip_opts` but
   appends `--system-site-packages` to `pip_opt`. A Bash probe with nounset
   enabled confirmed that `pip_opts` remains empty; the subsequent venv command
   uses `pip_opts`, so `site` mode does not receive the requested flag. The
   2026-10-16 offline WSL build reproduced the consequence: the generated venv
   could not import `setuptools` during Python extension metadata preparation.
   Creating a system-site venv manually and invoking the build in
   `disable`/offline mode worked around the issue without changing source.
2. **Build-script error detail is discarded.** `update_openEMS.sh` calls
   `die` with explanatory arguments, but `die` prints only a generic message.
   Running `bash ./update_openEMS.sh --njobs=` produced only “A fatal error
   has occurred!” and exit status 1 rather than the specific option error.

These are root orchestration findings; no source fix was made as part of this
migration audit.

## Validation and open work

- `bash -n` passed for `update_openEMS.sh` and all four tracked scripts under
  `scripts/`.
- `update_openEMS.sh` completed a full Ubuntu WSL build with GUI, Python, and
  CTB enabled; a second root build with `--with-hyp2mat` also succeeded.
  QCSXCAD/AppCSXCAD linked against Qt6/VTK, and `hyp2mat --help` ran.
- The CSXCAD C++ tests passed (2/2), its Python suite passed (150 tests, one
  skipped), the openEMS Python unit/simulation suite passed (31/31), the
  Octave suite passed (10/10), both MSL smoke tests passed, and `make html`
  completed with zero warnings. Exact commands are in `../VALIDATION.md`.
- The migration coverage CSV has 27 data rows, six columns, and consistent row
  widths. It is still a grouped coverage index, not a complete
  per-file/per-function contract map.
- No cross-platform CI run or interactive GUI test was performed.
- Root scripts are Bash-based; supported OS/package-manager behavior still
  requires execution in the documented Linux, macOS, and FreeBSD environments.
- The dependency checker and help text should be compared against the optional
  hyp2mat dependency requirements before changing the installation contract.
