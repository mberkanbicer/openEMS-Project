#!/usr/bin/env bash
# Differential check of the operator coefficients (RM-042/RM-043/RM-078).
#
# Native `--debug-operator` writes `vv`/`vi`/`ii`/`iv` as three-component point
# data in a compressed `.vtr`; the Rust CLI writes the same fields as legacy
# ASCII `.vtk` vectors. Compare them node by node. The native arrays are
# Float32, so the bound is 1e-6 of the field peak.
#
# Usage: scripts/ci/run_operator_dump_check_wsl.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NATIVE_BIN="${NATIVE_BIN:-$HOME/opt/openEMS/bin/openEMS}"
RUST_BIN="${RUST_BIN:-$REPO_ROOT/target/release/openems-cli}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

LINES="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20"
cat > "$WORK/pml.xml" <<EOF
<openEMS>
  <FDTD NumberOfTimesteps="5" TimeStepMethod="3">
    <BoundaryCond xmin="PML" xmax="PML" ymin="PML" ymax="PML" zmin="PML" zmax="PML"/>
    <Excitation Type="0" f0="1e9" fc="2e9"/>
  </FDTD>
  <ContinuousStructure CoordSystem="0">
    <RectilinearGrid DeltaUnit="0.001">
      <XLines>$LINES</XLines>
      <YLines>$LINES</YLines>
      <ZLines>$LINES</ZLines>
    </RectilinearGrid>
    <BackgroundMaterial Epsilon="4" Mue="1" Sigma="0.01" Kappa="0.0"/>
    <Properties/>
  </ContinuousStructure>
</openEMS>
EOF

mkdir -p "$WORK/native" "$WORK/rust"
( cd "$WORK/native" && "$NATIVE_BIN" ../pml.xml --no-simulation --debug-operator >log 2>&1 )
( cd "$WORK/rust" && "$RUST_BIN" ../pml.xml --no-simulation --debug-operator >log 2>&1 )

if [ ! -f "$WORK/native/operator_dump.vtr" ]; then
  echo "native operator dump missing" >&2
  tail -5 "$WORK/native/log" >&2
  exit 1
fi
if [ ! -f "$WORK/rust/operator_dump.vtk" ]; then
  echo "Rust operator dump missing" >&2
  tail -5 "$WORK/rust/log" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/compare_operator_dump.py" \
  "$WORK/native/operator_dump.vtr" "$WORK/rust/operator_dump.vtk" 1.0e-6
status=$?
if [ "$status" -ne 0 ]; then
  echo "operator dump check: FAIL"
  exit 1
fi
echo "operator dump check: PASS"
