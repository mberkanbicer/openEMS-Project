# Windows package (Rust migration)

**Date:** 2026-11-02
**Scope:** PKG-001 / E-012. Builds and verifies a Windows x64 package for the
Rust migration, the counterpart of the native `windows-package.yml` artifact.

## Artifact

| field | value |
| --- | --- |
| file | `dist/openEMS-rust_v0.37.0-130-g5b64b4a_win64.zip` |
| size | 14 715 410 bytes |
| SHA-256 | `c35beb63ca8a899c44f10ca1c6ba2ff5f4811b143e5bcca592a185eb07a7e0e5` |
| repository revision | `a7711c9` (openEMS `v0.37.0-130-g5b64b4a`) |
| compiler | `rustc 1.99.1 (58cf8f9c3 2026-10-13)` |
| Python wheel | `cp39-abi3-win_amd64` (Python 3.9-3.14, stable ABI), built on CPython 3.11.16 |
| solver features | `gpu` (the packaged `openems-cli` accepts `--gpu`) |

The zip is build output and is not committed (`/dist/` is ignored); the script
and the recorded hash make it reproducible. The hash pins this build because zip
timestamps change between runs; a rebuild reproduces the contents, not the exact
archive bytes. This build is the first one that carries the tutorials
(`tutorials/`), the probe/dump output-layer fixes (`openEMS@92a406a`) and the
RM-184 missing-excitation parity (`openEMS@5b64b4a`); it was rebuilt after the
24/24 acceptance run at `b5b5d00`.

## Contents

```
openEMS-rust_v0.37.0-130-g5b64b4a_win64/
  bin/    openems-cli.exe (GPU build), nf2ff-cli.exe, sar-cli.exe, ctb.exe,
          hyp2mat.exe, appcsxcad.exe
          hdf5.dll, zlib.dll, MSVC CRT
  python/ csxcad-0.1.0-cp39-abi3-win_amd64.whl (750 909 bytes)
          openems-0.1.0-cp39-abi3-win_amd64.whl (925 211 bytes)
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

## Verification (measured 2026-11-02, build `a7711c9` / `5b64b4a`)

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
package : ...\openEMS-rust_v0.37.0-130-g5b64b4a_win64.zip
size    : 14715410 bytes
sha256  : c35beb63ca8a899c44f10ca1c6ba2ff5f4811b143e5bcca592a185eb07a7e0e5
```

The closure step copies `bin\` to a scratch directory, sets `PATH` to
`%SystemRoot%\System32;%SystemRoot%` and solves a model there. It is part of the
script, so an incomplete runtime closure fails the build instead of the first
run on a user machine.

An independent extraction test unzipped the artifact to a scratch directory,
restricted `PATH` the same way and ran the packaged binaries (fresh run, not the
build's own smoke):

| check | result |
| --- | --- |
| SHA-256 of the zip (`certutil`) | `c35beb63ca8a899c44f10ca1c6ba2ff5f4811b143e5bcca592a185eb07a7e0e5` (matches) |
| `openems-cli -h` | PASS (exit 0, version banner, `--gpu` listed) |
| 20-step FDTD run from the package | PASS, exit 0, `simulation completed: 20 timesteps` |
| 20-step run with `--gpu` | PASS, exit 0, completed |
| 20-step run with an HDF5 `DumpBox` (writes `Et.h5`) | PASS, exit 0, 12 080 bytes, `FieldData/TD` frame `(3,3,3,3)` float32 plus `Mesh/{x,y,z}` |
| `appcsxcad.exe` launched from the extracted package | PASS (process alive after 5 s, window title `AppCSXCAD`) |
| wheels in a fresh `--system-site-packages` venv (`pip install --no-deps` from the package) | PASS: `CSXCAD`, `openEMS._openems`, `openEMS(NrTS=10)` + `SetCSX` + `Write2XML` produce a 682-byte XML |
| extracted package solves without conda on `PATH` | PASS (same 20-step run, `System32` only) |

GPU correctness and the host-sync trade-off are covered by the acceptance run
and by E-016 rather than by a single benchmark line: the acceptance GPU check at
`b5b5d00` measured `48^3`, 120 steps, `E diff 0.00e0`, CPU 3.21 s vs GPU 12.26 s
for the **host-sync extension** path. On the CLI, `--gpu` is slower for small or
extension-dominated models and only wins near half a million cells; the
2026-11-02 measurements are in `EXCEPTIONS.md` E-016. `--gpu` remains opt-in and
the default engine selection is unchanged.

Test suites on this source tree: `cargo test --release --workspace --features
"openems-core/hdf5,openems-core/gpu,openems-cli/gpu"` is green (openems-core
310 + 2 analytic tests, the CLI contract suite, the MATLAB ABI and Python
contract suites, CSXCAD and the GUI crates); `csxcad-core` alone passes 209.
The full-stack WSL acceptance run at `b5b5d00` is 24/24 PASS (859 crate tests,
Octave 10/10, performance gate within 4.0x wall / 3.25x RSS).

## Reproduce

```powershell
$env:HDF5_LIB_DIR = "<conda>\Library\lib"
$env:HDF5_INCLUDE_DIR = "<conda>\Library\include"
$env:PATH = "<conda>\Library\bin;$env:PATH"
pwsh scripts/ci/build_windows_package.ps1 -Python <conda>\python.exe
# CPU-only solver: -Features ""
```

Use `pwsh` (PowerShell 7), as above. Under Windows PowerShell 5.1 the same
script aborts at the first smoke step when the caller also redirects stderr
(`powershell -File ... 2>&1`): PS 5.1 turns the solver's
`[openEMS] Warning: ...` stderr line into a terminating `NativeCommandError`.
The script is unchanged by this; it is a host/redirection interaction worth
knowing when reproducing the build from a CI wrapper.

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
