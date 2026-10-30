#!/usr/bin/env python3
"""Gate a performance run against the recorded native baseline.

Reads the CSV produced by ``scripts/ci/run_performance_baseline_wsl.sh`` and
checks two proposed limits per case:

* wall time (Rust best / native best) <= ``--max-wall-ratio`` (default 4.0)
* peak RSS (Rust max / native max) <= ``--max-rss-ratio`` (default 3.25)

The limits are a proposal pending owner approval; this script only reports what
the recorded data shows. It exits non-zero when a limit is exceeded so it can be
wired into CI once the limits are accepted.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    if not rows:
        raise SystemExit(f"{path}: no rows")

    best: dict[tuple[str, str], dict[str, dict[str, float]]] = defaultdict(dict)
    for row in rows:
        key = (row["config"], row["case"])
        solver = row["solver"]
        wall = float(row["wall_s_best"])
        rss = float(row["peak_rss_mib_max"])
        current = best[key].get(solver)
        if current is None:
            best[key][solver] = {"wall": wall, "rss": rss}
        else:
            current["wall"] = min(current["wall"], wall)
            current["rss"] = max(current["rss"], rss)
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/migration/reference-data/perf/performance-baseline.csv",
    )
    parser.add_argument("--max-wall-ratio", type=float, default=4.0)
    parser.add_argument("--max-rss-ratio", type=float, default=3.25)
    args = parser.parse_args()

    best = load(Path(args.csv))
    failures = 0
    print(f"{'config':8} {'case':9} {'wall rust/native':>17} {'RSS rust/native':>16}  result")
    for (config, case), solvers in sorted(best.items()):
        if "native" not in solvers or "rust" not in solvers:
            print(f"{config:8} {case:9} missing native or rust rows")
            failures += 1
            continue
        wall_ratio = solvers["rust"]["wall"] / solvers["native"]["wall"]
        rss_ratio = solvers["rust"]["rss"] / solvers["native"]["rss"]
        ok = wall_ratio <= args.max_wall_ratio and rss_ratio <= args.max_rss_ratio
        failures += 0 if ok else 1
        print(
            f"{config:8} {case:9} "
            f"{solvers['rust']['wall']:6.2f}/{solvers['native']['wall']:5.2f} "
            f"= {wall_ratio:5.2f}x "
            f"{solvers['rust']['rss']:6.1f}/{solvers['native']['rss']:6.1f} "
            f"= {rss_ratio:5.2f}x  {'PASS' if ok else 'FAIL'}"
        )

    print(
        f"\nlimits: wall <= {args.max_wall_ratio:.2f}x, RSS <= {args.max_rss_ratio:.2f}x "
        "(proposed; owner approval pending)"
    )
    if failures:
        print(f"performance gate: FAIL ({failures} case(s))")
        return 1
    print("performance gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
