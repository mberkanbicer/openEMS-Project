#!/usr/bin/env bash
# UPML differential check (RM-043).
#
# 41 x 21 x 21 cells at 1 mm, eight-cell UPML on all six faces, hard E_z
# Gaussian at the centre, two E-field probes (centre and 6 mm off-centre).
# The native and Rust probe traces must agree within the approved 1 % RMS
# probe bound; the absorbed tail is also measured on both traces.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/openems-exact/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

X="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40"
Y="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20"
cat > "$WORK/upml.xml" <<EOF
<openEMS>
  <FDTD NumberOfTimesteps="900" endCriteria="0" TimeStepMethod="3">
    <Excitation Type="0" f0="6e9" fc="3e9"/>
    <BoundaryCond xmin="PML_8" xmax="PML_8" ymin="PML_8" ymax="PML_8" zmin="PML_8" zmax="PML_8"/>
  </FDTD>
  <ContinuousStructure CoordSystem="0">
    <RectilinearGrid DeltaUnit="0.001">
      <XLines>$X</XLines>
      <YLines>$Y</YLines>
      <ZLines>$Y</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="1" Mue="1" Sigma="0" Kappa="0"/>
    <Properties>
      <Excitation Name="src" Type="1" Excite="0,0,1">
        <Primitives><Box Priority="0"><P1 X="20" Y="10" Z="10"/><P2 X="20" Y="10" Z="11"/></Box></Primitives>
      </Excitation>
      <ProbeBox Name="p1" Type="2">
        <Primitives><Box Priority="0"><P1 X="20" Y="10" Z="10"/><P2 X="20" Y="10" Z="10"/></Box></Primitives>
      </ProbeBox>
      <ProbeBox Name="p2" Type="2">
        <Primitives><Box Priority="0"><P1 X="26" Y="10" Z="10"/><P2 X="26" Y="10" Z="10"/></Box></Primitives>
      </ProbeBox>
    </Properties>
  </ContinuousStructure>
</openEMS>
EOF

mkdir -p "$WORK/native" "$WORK/rust"
cp "$WORK/upml.xml" "$WORK/native/"
cp "$WORK/upml.xml" "$WORK/rust/"
( cd "$WORK/native" && "$NATIVE_BIN" upml.xml >log 2>&1 )
( cd "$WORK/rust" && "$RUST_BIN" upml.xml >log 2>&1 )

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

def tail_ratio(trace):
    peak = max(max(abs(value) for value in row[1:]) for row in trace) or 1.0
    tail = max(max(abs(value) for value in row[1:]) for row in trace[-20:])
    return tail / peak

print(f"p1 (centre): max relative difference {diff1 / peak:.3e}, tail {20 * __import__('math').log10(tail_ratio(a)):.0f} dB")
print(f"p2 (6 mm):   max relative difference {diff2 / peak:.3e}, tail {20 * __import__('math').log10(tail_ratio(c)):.0f} dB")
print(f"tail ratio native p1 {tail_ratio(a):.3e}, rust p1 {tail_ratio(b):.3e}")

bound = 1.0e-2
if max(diff1, diff2) / peak > bound:
    raise SystemExit(f"UPML traces differ from native by more than {bound:.0e} of the peak")
print("UPML check: PASS")
PY
