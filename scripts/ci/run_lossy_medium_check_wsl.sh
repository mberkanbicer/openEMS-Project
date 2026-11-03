#!/usr/bin/env bash
# Lossy-medium differential check (RM-054).
#
# Runs a parallel-plate TEM guide (PEC plates in z, PMC walls in y, PML in x)
# filled with Kappa=0.05 S/m through the pinned native binary and the Rust CLI
# and compares the E-field probe traces at x=60 mm and x=100 mm. This is the
# native comparison for the electric-conductivity path (`EC_G`); the analytic
# attenuation is not used as the bound because the native discretisation shows
# the same residual as the port.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/openems-exact/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

X="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120"
cat > "$WORK/lossy.xml" <<EOF
<openEMS>
  <FDTD NumberOfTimesteps="800" endCriteria="0" TimeStepMethod="3">
    <Excitation Type="0" f0="8e9" fc="8e9"/>
    <BoundaryCond xmin="PML_4" xmax="PML_4" ymin="PMC" ymax="PMC" zmin="PEC" zmax="PEC"/>
  </FDTD>
  <ContinuousStructure CoordSystem="0">
    <RectilinearGrid DeltaUnit="0.001">
      <XLines>$X</XLines>
      <YLines>0,1,2,3,4,5,6,7,8,9,10</YLines>
      <ZLines>0,1,2,3,4,5,6,7,8,9,10</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="1" Mue="1" Sigma="0" Kappa="0"/>
    <Properties>
      <Material Name="lossy">
        <Property Epsilon="1" Mue="1" Kappa="0.05" Sigma="0"/>
        <Primitives><Box Priority="1"><P1 X="-1" Y="-1" Z="-1"/><P2 X="130" Y="20" Z="20"/></Box></Primitives>
      </Material>
      <Excitation Name="src" Type="1" Excite="0,0,1">
        <Primitives><Box Priority="0"><P1 X="10" Y="0" Z="0"/><P2 X="10" Y="10" Z="10"/></Box></Primitives>
      </Excitation>
      <ProbeBox Name="p1" Type="2">
        <Primitives><Box Priority="0"><P1 X="60" Y="5" Z="5"/><P2 X="60" Y="5" Z="5"/></Box></Primitives>
      </ProbeBox>
      <ProbeBox Name="p2" Type="2">
        <Primitives><Box Priority="0"><P1 X="100" Y="5" Z="5"/><P2 X="100" Y="5" Z="5"/></Box></Primitives>
      </ProbeBox>
    </Properties>
  </ContinuousStructure>
</openEMS>
EOF

mkdir -p "$WORK/native" "$WORK/rust"
cp "$WORK/lossy.xml" "$WORK/native/"
cp "$WORK/lossy.xml" "$WORK/rust/"
( cd "$WORK/native" && "$NATIVE_BIN" lossy.xml >log 2>&1 )
( cd "$WORK/rust" && "$RUST_BIN" lossy.xml >log 2>&1 )

if [ ! -f "$WORK/native/p1" ] || [ ! -f "$WORK/rust/p1" ]; then
  echo "probe output missing" >&2
  tail -5 "$WORK/native/log" "$WORK/rust/log" >&2
  exit 1
fi

python3 - "$WORK/native/p1" "$WORK/rust/p1" "$WORK/native/p2" "$WORK/rust/p2" <<'PY'
import sys


def rows(path):
    out = []
    for line in open(path):
        parts = line.split()
        if len(parts) >= 4:
            try:
                out.append(tuple(float(value) for value in parts[:4]))
            except ValueError:
                pass
    return out


a = rows(sys.argv[1])
b = rows(sys.argv[2])
c = rows(sys.argv[3])
d = rows(sys.argv[4])
if not a or not b or not c or not d:
    raise SystemExit("empty probe output")

peak = max(max(abs(value) for value in row[1:]) for row in a) or 1.0
n = min(len(a), len(b))
diff1 = max(abs(a[i][k] - b[i][k]) for i in range(n) for k in (1, 2, 3))
n = min(len(c), len(d))
diff2 = max(abs(c[i][k] - d[i][k]) for i in range(n) for k in (1, 2, 3))
ratio = max(abs(row[3]) for row in c) / max(abs(row[3]) for row in a)

print(f"p1 (x=60 mm): max relative difference {diff1 / peak:.3e}")
print(f"p2 (x=100 mm): max relative difference {diff2 / peak:.3e}")
print(f"native probe ratio p2/p1: {ratio:.4f}")

bound = 1.0e-4
if max(diff1, diff2) / peak > bound:
    raise SystemExit(f"lossy guide differs from native by more than {bound:.0e}")
print("lossy medium check: PASS")
PY
