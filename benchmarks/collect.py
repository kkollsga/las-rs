#!/usr/bin/env python3
"""Collect benchmark results from pytest-benchmark JSON into results.csv.

Uses UPSERT semantics: for a given (version, library, benchmark) key, new
results UPDATE the existing row rather than appending a duplicate.  This
means you can re-run a subset of benchmarks and only those rows get
refreshed — other results for the same version are preserved.

Usage:
    # After running benchmarks with --benchmark-json:
    pytest benchmarks/bench_read.py --benchmark-only --benchmark-json=out.json
    python benchmarks/collect.py out.json --version 0.1.0

    # Collect from multiple JSON files:
    python benchmarks/collect.py benchmarks/results/*.json --version 0.1.0

    # Tag with a specific library name:
    python benchmarks/collect.py out.json --version 0.1.0 --library lasio

    # Dry-run — print what would change without writing:
    python benchmarks/collect.py out.json --version 0.1.0 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RESULTS_FILE = Path(__file__).parent / "results.csv"

COLUMNS = [
    "version",
    "library",
    "timestamp",
    "group",
    "benchmark",
    "min_s",
    "mean_s",
    "median_s",
    "stddev_s",
    "ops",
    "rounds",
    "rows",
    "curves",
    "file_mb",
]

# The composite key that identifies a unique benchmark result.
# Re-running the same benchmark for the same version+library updates the row.
KEY_COLS = ("version", "library", "benchmark")

# ---------------------------------------------------------------------------
# Infer file metadata from benchmark name
# ---------------------------------------------------------------------------

_SIZE_HINTS = {
    "tiny": (100, 4),
    "small": (1_000, 8),
    "medium": (100_000, 8),
    "large": (1_000_000, 8),
    "wide": (10_000, 200),
    "wrapped": (100_000, 30),
    "nulls": (100_000, 8),
    "single_curve": (1_000_000, 1),
}


def _infer_size(name: str) -> tuple[str, str]:
    for hint, (rows, curves) in _SIZE_HINTS.items():
        if hint in name:
            return str(rows), str(curves)
    return "", ""


# ---------------------------------------------------------------------------
# Parse one pytest-benchmark JSON file
# ---------------------------------------------------------------------------


def parse_json(path: Path, version: str, library: str, timestamp: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)

    rows = []
    for bench in data.get("benchmarks", []):
        name = bench["name"]
        group = bench.get("group", "")
        stats = bench["stats"]
        inferred_rows, inferred_curves = _infer_size(name)

        rows.append({
            "version": version,
            "library": library,
            "timestamp": timestamp,
            "group": group,
            "benchmark": name,
            "min_s": f"{stats['min']:.6f}",
            "mean_s": f"{stats['mean']:.6f}",
            "median_s": f"{stats['median']:.6f}",
            "stddev_s": f"{stats['stddev']:.6f}",
            "ops": f"{stats['ops']:.2f}",
            "rounds": str(stats["rounds"]),
            "rows": inferred_rows,
            "curves": inferred_curves,
            "file_mb": "",
        })

    return rows


# ---------------------------------------------------------------------------
# Load / save CSV
# ---------------------------------------------------------------------------


def _load_csv() -> list[dict]:
    """Load all existing rows from results.csv."""
    if not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size < 10:
        return []
    with open(RESULTS_FILE, newline="") as f:
        return list(csv.DictReader(f))


def _save_csv(rows: list[dict]) -> None:
    """Write all rows to results.csv (full rewrite)."""
    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row_key(row: dict) -> tuple:
    return tuple(row.get(k, "") for k in KEY_COLS)


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


def upsert_rows(new_rows: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """Upsert new results into results.csv.

    Returns (updated_count, inserted_count).
    """
    existing = _load_csv()
    index: dict[tuple, int] = {}
    for i, row in enumerate(existing):
        index[_row_key(row)] = i

    updated = 0
    inserted = 0

    for new_row in new_rows:
        key = _row_key(new_row)
        if key in index:
            if not dry_run:
                existing[index[key]] = new_row
            updated += 1
        else:
            if not dry_run:
                index[key] = len(existing)
                existing.append(new_row)
            inserted += 1

    if not dry_run:
        _save_csv(existing)

    return updated, inserted


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Collect pytest-benchmark JSON results into results.csv (upsert)"
    )
    parser.add_argument("files", nargs="+", help="pytest-benchmark JSON file(s)")
    parser.add_argument("--version", required=True, help="Library version tag (e.g. 0.1.0)")
    parser.add_argument("--library", default="las_rs", help="Library name (default: las_rs)")
    parser.add_argument("--timestamp", default=None, help="Override timestamp (ISO format)")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    timestamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_rows = []
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"Warning: {path} not found, skipping", file=sys.stderr)
            continue
        rows = parse_json(path, args.version, args.library, timestamp)
        print(f"Parsed {len(rows)} benchmarks from {path.name}")
        all_rows.extend(rows)

    if not all_rows:
        print("No results to collect.")
        return

    updated, inserted = upsert_rows(all_rows, dry_run=args.dry_run)

    tag = "[dry-run] " if args.dry_run else ""
    print(f"\n{tag}{updated} updated, {inserted} inserted in {RESULTS_FILE}")
    if not args.dry_run:
        total = sum(1 for _ in open(RESULTS_FILE)) - 1
        print(f"Total rows: {total}")


if __name__ == "__main__":
    main()
