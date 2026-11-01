# Windows package (Rust migration)

**Date:** 2026-11-02
**Scope:** PKG-001 / E-012. Builds and verifies a Windows x64 package for the
Rust migration, the counterpart of the native `windows-package.yml` artifact.

## Artifact

| field | value |
| --- | --- |
| file | `dist/openEMS-rust_v0.37.0-128-ga7d33e4_win64.zip` |
| size | 14 715 920 bytes |
| SHA-256 | `438d219d1b7fcbd7018c753ee9b692ec0dc3972b7e5c01d1f4dd7a0585629f91` |
| repository revision | `56b431b` (openEMS `v0.37.0-128-ga7d33e4`) |
| compiler | `rustc 1.99.1 (58cf8f9c3 2026-10-13)` |
| Python wheel | `cp39-abi3-win_amd64` (Python 3.9-3.14, stable ABI) |
| solver features | `gpu` (the packaged `openems-cli` accepts `--gpu`) |

The zip is build output and is not committed (`/dist/` is ignored); the script
and the recorded hash make it reproducible. The hash pins this build because zip
timestamps change between runs; a rebuild reproduces the contents, not the exact
archive bytes.

## Contents

```
openEMS-rust_v0.37.0-128-ga7d33e4_win64/
  bin/    openems-cli.exe (GPU build), nf2ff-cli.exe, sar-cli.exe, ctb.exe,
          hyp2mat.exe, appcsxcad.exe
          hdf5.dll, zlib.dll, MSVC CRT
  python/ csxcad-0.1.0-cp39-abi3-win_amd64.whl
          openems-0.1.0-cp39-abi3-win_amd64.whl
  README.txt, VERSION.txt
```

The DLL closure comes from a recursive `dumpbin /dependents` walk seeded by the
executables and resolved only in the HDF5 `Library\bin` directory named by
`HDF5_LIB_DIR`, so no System32 or toolchain DLLs leak into the package. The walk
treats any DLL that Windows ships in `System32` as an OS component and never
stages it.

How many DLLs get staged depends on the HDF5 the build links:

| conda env | HDF5 | extra DLLs |
| --- | --- | --- |
| `openems` (defaults) | 1.10.6 | `zlib.dll` only |
| `openems-gui` (conda-forge) | 1.14.4 | `zlib`, `szip`, `libcurl`, `libssh2`, `libcrypto`/`libssl`, `brotli*`, `libzstd` |

The recorded artifact was built against HDF5 1.10.6, so the solver path ships two
non-CRT DLLs. Whatever the closure is, the `smoke: DLL closure without conda on
PATH` step proves it is complete before the zip is written.

## Verification (measured 2026-11-02)

The script builds, smoke-tests and archives in one run:

```
== smoke: CLI help
 Version: 0.1.0 (Rust migration)
== smoke: CLI solves a tiny model
[openEMS] FDTD simulation completed: 20 timesteps.
== smoke: DLL closure without conda on PATH
[openEMS] FDTD simulation completed: 20 timesteps.
== smoke: Python wheels
wheel smoke ok: csxcad_py openEMS._openems 679
package : ...\openEMS-rust_v0.37.0-128-ga7d33e4_win64.zip
sha256  : 438d219d...
```

The closure step copies `bin\` to a scratch directory, sets `PATH` to
`%SystemRoot%\System32;%SystemRoot%` and solves a model there. It is part of the
script, so an incomplete runtime closure fails the build instead of the first
run on a user machine.

An independent extraction test unzipped the artifact to a scratch directory,
restricted `PATH` the same way and ran the packaged binaries:

| check | result |
| --- | --- |
| `openems-cli -h` | PASS (version banner, `--gpu` listed) |
| 20-step FDTD run from the package | PASS, exit 0 |
| 40-step run with an HDF5 `DumpBox` (writes `Et.h5`) | PASS, exit 0, valid HDF5 (`FieldData/TD` `(3,11,11,11)` float32 + `Mesh/{x,y,z}`) |
| 48³ / 120-step model with `--gpu` | PASS, exit 0 (`FDTD simulation completed: 120 timesteps`) |
| `appcsxcad.exe` launched from the extracted package | PASS (window process stays up, no stderr) |
| wheel import from a clean venv | PASS (`CSXCAD`, `openEMS._openems`) |
| wheel writes a CSXCAD XML | PASS (679 bytes) |
| extracted package without conda on `PATH` | PASS, exit 0 |

GPU correctness on the same build (`cargo test -p openems-core --features "hdf5 gpu" --release`):

```
GPU round-trip on NVIDIA GeForce RTX 5070 Laptop GPU (Vulkan)
GPU update vs CPU ...: E 5.96e-8, H 5.96e-8
GPU engine vs CPU: 48^3, 120 steps, E diff 0.00e0, CPU 432.13ms, GPU 27.07ms
GPU host extension vs CPU: 48^3, 120 steps, E diff 0.00e0, CPU 441.16ms, GPU 2.50s
```

`cargo test --release -p openems-core --features "hdf5 gpu"` passes 308 tests;
`cargo test --release -p csxcad-core` passes 209.

The host-sync extension path is deliberately slower than the CPU kernel: every
step with PML or other extensions downloads the fields, runs the CPU extension
and uploads again. Models without extensions keep the fields resident and the
GPU kernel wins by ~16x (27 ms vs 432 ms above). This matches ADR 0012.

## Reproduce

```powershell
$env:HDF5_LIB_DIR = "<conda>\Library\lib"
$env:HDF5_INCLUDE_DIR = "<conda>\Library\include"
$env:PATH = "<conda>\Library\bin;$env:PATH"
pwsh scripts/ci/build_windows_package.ps1 -Python <conda>\python.exe
# CPU-only solver: -Features ""
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
- `-match` in PowerShell is culture-aware. Before 2026-11-02 the DLL walk used
  it against a lowercase system-DLL pattern, so on a Turkish locale
  `PSAPI.DLL`/`ADVAPI32.dll` did not match and the walk printed false gaps; it
  now compares invariant-lowercased names and also consults `System32`.
