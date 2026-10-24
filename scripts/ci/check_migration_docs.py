#!/usr/bin/env python3
"""Check that the migration records are internally consistent.

Verifies:
  * every ``RM-###`` row in REMEDIATION_TASKS.md uses the closed status
    vocabulary;
  * the "Current status snapshot" counts match the task table;
  * the remaining-backlog header matches the number of `Not Started` rows;
  * MIGRATION_STATUS.md and COVERAGE_MATRIX.csv only use the closed vocabulary.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "docs" / "migration"
VOCABULARY = {
    "Not Started",
    "Analyzed",
    "Implemented",
    "Integrated",
    "Verified",
    "Blocked",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_tasks() -> list[str]:
    problems: list[str] = []
    path = MIGRATION / "REMEDIATION_TASKS.md"
    text = read(path)
    rows = re.findall(
        r"^\| (RM-\d{3}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$",
        text,
        flags=re.MULTILINE,
    )
    if not rows:
        return ["no task rows found in REMEDIATION_TASKS.md"]
    counts: Counter[str] = Counter()
    for row in rows:
        status = row[6].strip()
        if status not in VOCABULARY:
            problems.append(f"{row[0]}: unknown status '{status}'")
        counts[status] += 1

    snapshot_rows = dict(
        re.findall(r"\| `([A-Za-z ]+)` \| (\d+) \|", text)
    )
    if not snapshot_rows:
        problems.append("status snapshot table not found")
    else:
        for status, value in snapshot_rows.items():
            if status in VOCABULARY and counts[status] != int(value):
                problems.append(
                    f"snapshot says {status}={value}, table has {counts[status]}"
                )

    backlog = re.search(r"## Remaining backlog \((\d+) tasks\)", text)
    if backlog:
        if int(backlog.group(1)) != counts["Not Started"]:
            problems.append(
                f"backlog header says {backlog.group(1)}, table has {counts['Not Started']} Not Started"
            )
    elif counts["Not Started"]:
        problems.append("remaining-backlog section missing")

    total = sum(counts.values())
    if total != len(rows):
        problems.append(f"counted {total} statuses for {len(rows)} rows")
    return problems


def check_status_doc() -> list[str]:
    problems: list[str] = []
    path = MIGRATION / "MIGRATION_STATUS.md"
    if not path.exists():
        return ["MIGRATION_STATUS.md missing"]
    text = read(path)
    for status in re.findall(r"\|\s*(Verified|Implemented|Integrated|Analyzed|Blocked|Not Started)\s*\|", text):
        if status not in VOCABULARY:
            problems.append(f"MIGRATION_STATUS.md: unknown status {status}")
    return problems


def check_coverage() -> list[str]:
    problems: list[str] = []
    path = MIGRATION / "COVERAGE_MATRIX.csv"
    if not path.exists():
        return ["COVERAGE_MATRIX.csv missing"]
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return ["COVERAGE_MATRIX.csv has no header"]
        status_column = next(
            (name for name in reader.fieldnames if "status" in name.lower()), None
        )
        if not status_column:
            return ["COVERAGE_MATRIX.csv has no status column"]
        for number, row in enumerate(reader, start=2):
            value = (row.get(status_column) or "").strip()
            if value and value not in VOCABULARY:
                problems.append(
                    f"COVERAGE_MATRIX.csv:{number}: unknown status '{value}'"
                )
    return problems


def main() -> int:
    problems = check_tasks() + check_status_doc() + check_coverage()
    if problems:
        print("migration record check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print("migration record check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
