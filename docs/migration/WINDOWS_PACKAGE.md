# Windows package (Rust migration)

**Date:** 2026-10-31
**Scope:** PKG-001 / E-012. Builds and verifies a Windows x64 package for the
Rust migration, the counterpart of the native `windows-package.yml` artifact.

## Artifact

| field | value |
| --- | --- |
| file | `dist/openEMS-rust_v0.37.0-112-g4af020f_win64.zip` |
| size | 15 460 986 bytes |
| SHA-256 | `f7a9c15c4cddfbed92a5b861c9e5c2d0c0db395a69fe94a1b14b145d962d611d` |
| repository revision | `85b728d` (openEMS `v0.37.0-112-g4af020f`) |
| compiler | `rustc 1.99.1` |
| Python wheel | `cp39-abi3-win_amd64` (Python 3.9-3.14, stable ABI) |

The zip is build output and is not committed (`/dist/` is ignored); the script
and the recorded hash make it reproducible. The hash pins this build because zip
timestamps change between runs; a rebuild reproduces the contents, not the exact
archive bytes.

## Contents

```
openEMS-rust_v0.37.0-112-g4af020f_win64/
  bin/    openems-cli.exe, nf2ff-cli.exe, sar-cli.exe, ctb.exe,
          hyp2mat.exe, appcsxcad.exe
          hdf5.dll, zlib.dll, szip.dll, libcurl.dll, libssh2.dll,
          libcrypto-3-x64.dll, brotli*.dll, MSVC CRT
  python/ csxcad-0.1.0-cp39-abi3-win_amd64.whl
          openems-0.1.0-cp39-abi3-win_amd64.whl
  README.txt, VERSION.txt
```

The DLL closure comes from a recursive `dumpbin /dependents` walk seeded by the
executables and resolved only in the HDF5/conda `Library\bin` directory, so no
System32 or toolchain DLLs leak into the package.

## Verification (measured 2026-10-31)

The script builds, smoke-tests and archives in one run:

```
== smoke: CLI help
 Version: 0.1.0 (Rust migration)
== smoke: CLI solves a tiny model
[openEMS] FDTD simulation completed: 20 timesteps.
== smoke: Python wheels
wheel smoke ok: csxcad_py openEMS._openems 679
package : ...\openEMS-rust_v0.37.0-112-g4af020f_win64.zip
sha256  : f7a9c15c...
```

An independent extraction test removed the conda directories from `PATH`,
unpacked the zip to a scratch directory and ran the packaged binary on the same
model: exit 0 with `FDTD simulation completed: 20 timesteps`, so the shipped DLL
set is complete for the solver path.

| check | result |
| --- | --- |
| `openems-cli -h` | PASS (version banner) |
| 20-step FDTD run from the package | PASS, exit 0 |
| extracted package without conda on `PATH` | PASS, exit 0 |
| wheel import from a clean venv | PASS (`CSXCAD`, `openEMS._openems`) |
| wheel import on CPython 3.14 | PASS (`csxcad_py`, `openEMS._openems`; abi3) |
| wheel writes a CSXCAD XML | PASS (679 bytes) |
| `appcsxcad.exe` packaged | present; not launched (GUI needs a desktop session) |

## Reproduce

```powershell
$env:HDF5_LIB_DIR = "<conda>\Library\lib"
$env:HDF5_INCLUDE_DIR = "<conda>\Library\include"
$env:PATH = "<conda>\Library\bin;$env:PATH"
pwsh scripts/ci/build_windows_package.ps1 -Python <conda>\python.exe
```

`.github/workflows/windows-rust-package.yml` runs the same script on
`windows-latest` with miniconda (HDF5 + numpy) and uploads the zip and its
`.sha256`. Actions are currently disabled at the account level (E-010), so the
workflow has not run on a hosted runner; the local run above is the recorded
evidence.

## Scope and limits

- The wheels are built with PyO3 abi3 (`cp39-abi3`), so one wheel covers
  CPython 3.9-3.14. Verified by importing both extensions on 3.11 (full package
  import) and 3.14 (extension modules) from clean virtual environments.
- The wheels link `hdf5.dll` from `bin\`. On Python 3.8+ `PATH` is not used for
  extension-module DLL resolution; call
  `os.add_dll_directory(r"...\bin")` before importing (the package smoke test
  does exactly this). h5py ships its own `hdf5.dll` under the same name, so do
  not expose both in one process.
- The native C++ `windows-package.yml` (Qt/AppCSXCAD, vcpkg) is untouched and
  remains a reference path. It has not run at this HEAD; it is not the migration
  deliverable and is not required by E-012's replacement.
