#!/usr/bin/env bash
# Differential check of the sampled excitation arrays (RM-037/RM-038/RM-039).
#
# Both solvers write `et` (voltage at n*dT) and `ht` (current at (n+0.5)*dT)
# next to their output. Run the pinned native binary and the Rust CLI on
# byte-identical input and compare the two files element by element. The
# samples are `FDTD_FLOAT` (f32) in both implementations and the native dump is
# written with six significant digits, so the bound is 1e-5 relative to the
# peak; the recorded runs sit at or below 2.6e-6.
#
# Usage: scripts/ci/run_excitation_dump_check_wsl.sh
#   NATIVE_BIN   native openEMS (default: ~/opt/openEMS/bin/openEMS)
#   RUST_BIN     Rust CLI      (default: <repo>/target/release/openems-cli)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/opt/openEMS/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ ! -x "$NATIVE_BIN" ]; then
  echo "native binary not found: $NATIVE_BIN" >&2
  exit 1
fi
if [ ! -x "$RUST_BIN" ]; then
  echo "Rust CLI not found: $RUST_BIN" >&2
  exit 1
fi

write_xml() {
  local path="$1" type="$2" extra="$3" fmax="$4"
  cat > "$path" <<EOF
<openEMS>
  <FDTD NumberOfTimesteps="10" TimeStepMethod="3" TimeStep="1.92583e-12" f_max="$fmax">
    <BoundaryCond xmin="PEC" xmax="PEC" ymin="PEC" ymax="PEC" zmin="PEC" zmax="PEC"/>
    <Excitation Type="$type" $extra/>
  </FDTD>
  <ContinuousStructure CoordSystem="0">
    <RectilinearGrid DeltaUnit="0.001">
      <XLines>0,1,2,3</XLines>
      <YLines>0,1,2,3</YLines>
      <ZLines>0,1,2,3</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="1" Mue="1" Sigma="0" Kappa="0"/>
    <Properties/>
  </ContinuousStructure>
</openEMS>
EOF
}

write_xml "$WORK/gauss.xml" 0 'f0="1e9" fc="2e9"' "3e9"
write_xml "$WORK/sinus.xml" 1 'f0="1e9"' "1e9"
write_xml "$WORK/dirac.xml" 2 'f_max="10e9"' "10e9"
write_xml "$WORK/step.xml" 3 'f_max="10e9"' "10e9"
write_xml "$WORK/custom2.xml" 10 'f0="1e9" Function="exp(-pow((t-5e-9)/1e-9,2))*sin(2*pi*1e9*t)"' "1e9"
write_xml "$WORK/custom.xml" 10 'f0="1e9" Function="sin(2*pi*1e9*t)"' "1e9"

status=0
for case in gauss sinus dirac step custom custom2; do
  mkdir -p "$WORK/native_$case" "$WORK/rust_$case"
  ( cd "$WORK/native_$case" && "$NATIVE_BIN" "../$case.xml" --no-simulation >native.log 2>&1 )
  ( cd "$WORK/rust_$case" && "$RUST_BIN" "../$case.xml" --no-simulation >rust.log 2>&1 )
  for signal in et ht; do
    if [ ! -f "$WORK/native_$case/$signal" ] || [ ! -f "$WORK/rust_$case/$signal" ]; then
      echo "[FAIL] $case/$signal missing (native or Rust)"
      status=1
      continue
    fi
    if ! python3 - "$WORK/native_$case/$signal" "$WORK/rust_$case/$signal" "$case" "$signal" <<'PY'
import sys
native_path, rust_path, case, signal = sys.argv[1:5]

def load(path):
    times, values = [], []
    with open(path) as handle:
        for line in handle:
            time, value = line.split()
            times.append(float(time))
            values.append(float(value))
    return times, values

nt, nv = load(native_path)
rt, rv = load(rust_path)
if len(nt) != len(rt):
    print(f"[FAIL] {case}/{signal}: sample count {len(nt)} vs {len(rt)}")
    sys.exit(1)
if not nt:
    print(f"[FAIL] {case}/{signal}: empty")
    sys.exit(1)
time_diff = max(abs(a - b) for a, b in zip(nt, rt))
peak = max(abs(value) for value in nv) or 1.0
value_diff = max(abs(a - b) for a, b in zip(nv, rv)) / peak
time_bound = 1.0e-6 * (max(abs(t) for t in nt) + 1.0)
if time_diff > time_bound or value_diff > 1.0e-5:
    print(f"[FAIL] {case}/{signal}: max|dt|={time_diff:.3e} max rel={value_diff:.3e}")
    sys.exit(1)
print(f"  {case:6}/{signal}: n={len(nt):5d} max|dt|={time_diff:.3e} max rel={value_diff:.3e}")
PY
    then
      status=1
    fi
  done
done

if [ "$status" -ne 0 ]; then
  echo "excitation dump check: FAIL"
  exit 1
fi
echo "excitation dump check: PASS"
