#!/usr/bin/env bash
# Native field dump check (RM-144).
#
# Runs a small closed cylindrical mesh through the pinned native binary and the
# Rust CLI with --nativeFieldDumps and compares the last time-domain dump. With
# the flag both keep the native (rho, alpha, z) components; a Cartesian run is
# unchanged. Bound: 1e-4 of the peak (the same class as the HDF5 snapshot
# bound).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/openems-exact/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/cyl.xml" <<'EOF'
<openEMS>
  <FDTD CylinderCoords="1" OverSampling="1000" NumberOfTimesteps="20" endCriteria="0">
    <Excitation Type="0" f0="1e9" fc="1e9"/>
    <BoundaryCond xmin="PEC" xmax="PEC" ymin="PEC" ymax="PEC" zmin="PEC" zmax="PEC"/>
  </FDTD>
  <ContinuousStructure CoordSystem="1">
    <RectilinearGrid DeltaUnit="0.001" CoordSystem="1">
      <XLines>1,2,3,4,5</XLines>
      <YLines>0,0.7853981633974483,1.5707963267948966,2.356194490192345,3.141592653589793,3.9269908169872414,4.71238898038469,5.497787143782138,6.283185307179586</YLines>
      <ZLines>0,1,2,3,4</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="1" Mue="1" Sigma="0" Kappa="0"/>
    <Properties>
      <Excitation Name="src" Type="1" Excite="1,0,0">
        <Primitives><Box Priority="0"><P1 X="2" Y="0" Z="0"/><P2 X="2" Y="6.283185307179586" Z="4"/></Box></Primitives>
      </Excitation>
      <DumpBox Name="edump" DumpType="0" FileType="0" DumpMode="1">
        <Primitives><Box Priority="0"><P1 X="1" Y="0" Z="0"/><P2 X="5" Y="6.283185307179586" Z="4"/></Box></Primitives>
      </DumpBox>
    </Properties>
  </ContinuousStructure>
</openEMS>
EOF

mkdir -p "$WORK/native" "$WORK/rust"
cp "$WORK/cyl.xml" "$WORK/native/"
cp "$WORK/cyl.xml" "$WORK/rust/"
( cd "$WORK/native" && "$NATIVE_BIN" cyl.xml --nativeFieldDumps >log 2>&1 )
( cd "$WORK/rust" && "$RUST_BIN" cyl.xml --nativeFieldDumps >log 2>&1 )

NATIVE_DUMP="$(ls "$WORK"/native/edump_* 2>/dev/null | tail -1)"
RUST_DUMP="$(ls "$WORK"/rust/edump_* 2>/dev/null | tail -1)"
if [ -z "$NATIVE_DUMP" ] || [ -z "$RUST_DUMP" ]; then
  echo "dump output missing" >&2
  tail -5 "$WORK/native/log" "$WORK/rust/log" >&2
  exit 1
fi

python3 - "$NATIVE_DUMP" "$RUST_DUMP" <<'PY'
import sys

import vtk
from vtk.util.numpy_support import vtk_to_numpy


def read(path):
    if path.endswith(".vts"):
        reader = vtk.vtkXMLStructuredGridReader()
    elif path.endswith(".vtr"):
        reader = vtk.vtkXMLRectilinearGridReader()
    else:
        reader = vtk.vtkStructuredGridReader()
    reader.SetFileName(path)
    reader.Update()
    grid = reader.GetOutput()
    array = grid.GetPointData().GetArray("E-Field")
    if array is None:
        names = [grid.GetPointData().GetArrayName(i) for i in range(grid.GetPointData().GetNumberOfArrays())]
        raise SystemExit(f"{path}: no E-Field array ({names})")
    return vtk_to_numpy(array)


a = read(sys.argv[1])
b = read(sys.argv[2])
if a.shape != b.shape:
    raise SystemExit(f"shape mismatch: {a.shape} vs {b.shape}")
peak = float(abs(a).max()) or 1.0
difference = float(abs(a - b).max())
print(f"points {a.shape[0]}, peak {peak:.4e}, max abs diff {difference:.3e}, relative {difference / peak:.3e}")
if difference / peak > 1.0e-4:
    raise SystemExit("native field dump differs by more than 1e-4 of the peak")
print("native field dump check: PASS")
PY
