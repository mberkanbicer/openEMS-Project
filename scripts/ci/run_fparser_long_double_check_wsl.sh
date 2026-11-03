#!/usr/bin/env bash
# Native differential for the fparser long-double backend (E-001).
#
# Builds FunctionParser_ld from the reference C++ sources, evaluates a small
# corpus at x=0.5, and compares it with the Rust binary128 backend. The Rust
# value is projected to f64 because the native x87 long double has a 64-bit
# mantissa and the Rust backend carries more precision; the parser semantics
# (grammar, optimizer rules, builtins) are compared at 1e-13 relative.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FPARSER="$REPO_ROOT/fparser"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

g++ -O2 -std=c++11 -DFP_SUPPORT_LONG_DOUBLE_TYPE -DFP_USE_STRTOLD \
    -I"$FPARSER" "$SCRIPT_DIR/fparser_long_double_oracle.cpp" \
    "$FPARSER/fparser.cc" "$FPARSER/fpoptimizer.cc" \
    -o "$WORK/oracle"

cat > "$WORK/corpus" <<'EOF'
1/3
0.1+0.2
sqrt(2)
sin(x)
cos(x)
tan(x)
asin(x)
acos(x)
atan(x)
exp(x)
log(x)
log10(x)
log2(x)
sinh(x)
cosh(x)
tanh(x)
asinh(x)
cbrt(x)
x^3
x^3.5
(1+x)^10
sin(x)^2+cos(x)^2
atan2(x, 0.25)
hypot(x, 0.3)
max(x, 0.7)
min(x, 0.7)
1/(1+x)
2^x
int(x+0.3)
abs(-x)
EOF

"$WORK/oracle" < "$WORK/corpus" > "$WORK/native"
(
    cd "$REPO_ROOT"
    cargo run -q -p fparser-rs --example long_double_probe --features long-double \
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

worst = 0.0
worst_expression = ""
failures = []
for expression, native_line, rust_line in zip(corpus, native, rust):
    if native_line.startswith("ERROR") or rust_line.startswith("ERROR"):
        both_error = native_line.startswith("ERROR") and rust_line.startswith("ERROR")
        if not both_error:
            failures.append((expression, native_line, rust_line))
        continue
    a = float(native_line)
    b = float(rust_line)
    if a == 0.0:
        relative = abs(b)
    else:
        relative = abs(a - b) / abs(a)
    if relative > worst:
        worst = relative
        worst_expression = expression
    if relative > 1.0e-13:
        failures.append((expression, a, b, relative))

if failures:
    for failure in failures:
        print("FAIL", failure)
    print(f"fparser long-double differential: FAIL (worst {worst:.3e} on {worst_expression})")
    raise SystemExit(1)

print(f"fparser long-double differential: PASS ({len(corpus)} expressions, "
      f"worst relative {worst:.3e} on {worst_expression})")
PY
