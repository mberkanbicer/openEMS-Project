#!/usr/bin/env python3
"""Compare the native and Rust `--debug-operator` dumps.

Native writes a compressed VTK XML rectilinear grid (`.vtr`, Float32 point
data, `vv`/`vi`/`ii`/`iv` as three-component arrays); the Rust CLI writes the
same fields as legacy ASCII VTK vectors. Both are read node by node and compared
component-wise, relative to the largest native magnitude of that field.

Usage: compare_operator_dump.py <native.vtr> <rust.vtk> [bound]
Exit code is non-zero when a field is missing or exceeds the bound.
"""

from __future__ import annotations

import base64
import re
import struct
import sys
import zlib

FIELDS = ("vv", "vi", "ii", "iv")


def decode_chunked_base64(text: str) -> bytes:
    """Decode VTK's concatenation of separately padded base64 chunks."""
    raw = "".join(text.split())
    out = bytearray()
    index = 0
    while index < len(raw):
        padding = raw.find("=", index)
        if padding == -1:
            out.extend(base64.b64decode(raw[index:]))
            break
        end = padding
        while end < len(raw) and raw[end] == "=":
            end += 1
        out.extend(base64.b64decode(raw[index:end]))
        index = end
    return bytes(out)


def read_native(path: str) -> dict[str, list[tuple[float, float, float]]]:
    text = open(path, encoding="utf-8", errors="replace").read()
    fields: dict[str, list[tuple[float, float, float]]] = {}
    for match in re.finditer(
        r'<DataArray[^>]*Name="(%s)"[^>]*format="binary"[^>]*>([^<]*)<'
        % "|".join(FIELDS),
        text,
        flags=re.DOTALL,
    ):
        name = match.group(1)
        payload = decode_chunked_base64(match.group(2))
        blocks, block_size, last_size = struct.unpack_from("<3I", payload, 0)
        offset = 12
        compressed_sizes = struct.unpack_from("<%dI" % blocks, payload, offset)
        offset += 4 * blocks
        raw = bytearray()
        for index, size in enumerate(compressed_sizes):
            chunk = payload[offset : offset + size]
            offset += size
            raw.extend(zlib.decompress(chunk))
        count_bytes = (blocks - 1) * block_size + last_size
        count = count_bytes // 4  # Float32 point data
        values = struct.unpack_from("<%df" % count, raw, 0)
        fields[name] = [
            (values[3 * i], values[3 * i + 1], values[3 * i + 2]) for i in range(count // 3)
        ]
    return fields


def read_rust(path: str) -> dict[str, list[tuple[float, float, float]]]:
    lines = open(path, encoding="utf-8").read().splitlines()
    fields: dict[str, list[tuple[float, float, float]]] = {}
    index = 0
    while index < len(lines):
        parts = lines[index].split()
        if parts and parts[0] == "VECTORS":
            name = parts[1]
            index += 1
            values = []
            while index < len(lines):
                row = lines[index].split()
                if len(row) != 3:
                    break
                try:
                    values.append((float(row[0]), float(row[1]), float(row[2])))
                except ValueError:
                    break
                index += 1
            fields[name] = values
            continue
        index += 1
    return fields


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    native_path, rust_path = sys.argv[1], sys.argv[2]
    bound = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0e-6

    native = read_native(native_path)
    rust = read_rust(rust_path)
    if not native:
        print("no native data arrays found", file=sys.stderr)
        return 1
    status = 0
    for name in FIELDS:
        if name not in native:
            print(f"[FAIL] native dump has no {name}")
            status = 1
            continue
        if name not in rust:
            print(f"[FAIL] Rust dump has no {name}")
            status = 1
            continue
        n_values, r_values = native[name], rust[name]
        if len(n_values) != len(r_values):
            print(f"[FAIL] {name}: node count {len(n_values)} vs {len(r_values)}")
            status = 1
            continue
        peak = max(max(abs(v) for v in point) for point in n_values) or 1.0
        worst = 0.0
        for n_point, r_point in zip(n_values, r_values):
            for a, b in zip(n_point, r_point):
                worst = max(worst, abs(a - b) / peak)
        verdict = "ok" if worst <= bound else "FAIL"
        if verdict == "FAIL":
            status = 1
        print(f"  {name}: nodes={len(n_values)} peak={peak:.6g} max rel diff={worst:.3e} {verdict}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
