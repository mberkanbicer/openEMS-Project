#!/usr/bin/env bash
# Native differential for the fparser long-integer backend (E-001).
#
# Builds FunctionParser_gmpint from the reference C++ sources (libgmp),
# evaluates the corpus at x=5 and compares exact integer results with the Rust
# rug::Integer backend. Expressions that native rejects must also be rejected
# by the Rust parser.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FPARSER="$REPO_ROOT/fparser"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

g++ -O2 -std=c++11 -DFP_SUPPORT_GMP_INT_TYPE \
    -I"$FPARSER" "$SCRIPT_DIR/fparser_long_integer_oracle.cpp" \
    "$FPARSER/fparser.cc" "$FPARSER/fpoptimizer.cc" "$FPARSER/mpfr/GmpInt.cc" \
    -lgmp -o "$WORK/oracle"

cat > "$WORK/corpus" <<'EOF'
1
0x10
0012
0x1F
7/3
-7/3
7%3
-7%3
5/0
5%0
abs(-7)
abs(7)
min(3,5)
max(3,5)
min(-3,2)
max(-3,2)
if(1, 2, 3)
if(0, 2, 3)
if(-1, 7, 9)
1=1
1!=2
1<=2
1>=2
1<2
1>0
!0
!2
!(-1)
-(-5)
--5
(7/3)*3
7/3*3
7/(3*3)
x
-x
x/2
x%2
x/2*2+x%2
1.5
1e3
2^10
2^-1
1&&2
1||2
sin(x)
sqrt(x)
int(7/2)
floor(7/2)
hypot(3,4)
atan2(3,4)
==1
1==1
EOF

"$WORK/oracle" < "$WORK/corpus" > "$WORK/native"
(
    cd "$REPO_ROOT"
    cargo run -q -p fparser-rs --example long_integer_probe --features long-integer \
        < "$WORK/corpus" > "$WORK/rust"
)

python3 - "$WORK/native" "$WORK/rust" "$WORK/corpus" <<'PY'
import sys

native = open(sys.argv[1]).read().splitlines()
rust = open(sys.argv[2]).read().splitlines()
corpus = [line for line in open(sys.argv[3]).read().splitlines() if line]

if len(native) != len(corpus) or len(rust) != len(corpus):
    print(f"shape mismatch: corpus={len(corpus)} native={len(native)} rust={len(rust)}")
    raise SystemExit(1)

failures = []
for expression, native_line, rust_line in zip(corpus, native, rust):
    native_error = native_line.startswith("PARSE_ERROR")
    rust_error = rust_line.startswith("ERROR")
    if native_error or rust_error:
        if native_error != rust_error:
            failures.append((expression, native_line, rust_line))
        continue
    if int(native_line) != int(rust_line):
        failures.append((expression, native_line, rust_line))

if failures:
    for failure in failures:
        print("FAIL", failure)
    print(f"fparser long-integer differential: FAIL ({len(failures)} mismatches)")
    raise SystemExit(1)

print(f"fparser long-integer differential: PASS ({len(corpus)} expressions, exact integers, "
      f"parse-error agreement)")
PY
