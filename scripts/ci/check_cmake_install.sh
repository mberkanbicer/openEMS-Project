#!/usr/bin/env bash
# Check the installed layout without building the native stack.
#
# The root CMake project installs the Rust binaries under their native names
# (`openEMS`, `AppCSXCAD`, `hyp2mat`, `nf2ff`, `sar_calc`, `ctb`) plus the
# MATLAB C ABI libraries and the M-files. Building all of it needs the native
# toolchain and the VTK/Qt dependencies, so this check configures the project
# with a fake `RUST_TARGET_DIR` populated with stub executables and runs the
# install step. It fails if a name or destination drifts.
#
# Usage: scripts/ci/check_cmake_install.sh
set -uo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/rust/release" "$WORK/prefix"
for binary in openems-cli appcsxcad hyp2mat nf2ff-cli sar-cli ctb; do
  printf '#!/bin/sh\nexit 0\n' > "$WORK/rust/release/$binary"
  chmod +x "$WORK/rust/release/$binary"
done
for library in libcsxcad_matlab.so libopenems_matlab.so; do
  : > "$WORK/rust/release/$library"
done

if ! cmake -S "$REPO_ROOT" -B "$WORK/build" \
    -DBUILD_RUST=YES \
    -DCMAKE_INSTALL_PREFIX="$WORK/prefix" \
    -DRUST_TARGET_DIR="$WORK/rust" > "$WORK/configure.log" 2>&1; then
  echo "cmake configure failed:" >&2
  tail -20 "$WORK/configure.log" >&2
  exit 1
fi

if ! cmake --install "$WORK/build" > "$WORK/install.log" 2>&1; then
  echo "cmake install failed:" >&2
  tail -20 "$WORK/install.log" >&2
  exit 1
fi

expected="AppCSXCAD ctb hyp2mat nf2ff openEMS sar_calc"
actual="$(ls "$WORK/prefix/bin" | tr '\n' ' ' | sed 's/ $//')"
if [ "$actual" != "$expected" ]; then
  echo "unexpected bin layout" >&2
  echo "  expected: $expected" >&2
  echo "  actual:   $actual" >&2
  exit 1
fi

for library in libcsxcad_matlab.so libopenems_matlab.so; do
  if [ ! -f "$WORK/prefix/lib/$library" ]; then
    echo "missing library: $library" >&2
    exit 1
  fi
done
for tree in CSXCAD openEMS; do
  if [ ! -d "$WORK/prefix/share/$tree/matlab" ]; then
    echo "missing M-file tree: share/$tree/matlab" >&2
    exit 1
  fi
done

echo "CMake install layout: $actual"
echo "MATLAB libraries and M-file trees installed"
