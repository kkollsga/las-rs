#!/usr/bin/env python3
"""Generate human-readable reports and charts from benchmark results.

Usage:
    # Print a table of the latest run:
    python benchmarks/report.py

    # Compare two versions:
    python benchmarks/report.py --compare 0.1.0 0.2.0

    # Compare las_rs vs lasio for a specific version:
    python benchmarks/report.py --vs-lasio 0.1.0

    # Filter to a specific group:
    python benchmarks/report.py --group read-scaling-rows

    # Generate charts (saves PNG files to benchmarks/charts/):
    python benchmarks/report.py --charts
    python benchmarks/report.py --compare 0.1.0 0.2.0 --charts

    # Export a markdown table (for README / PR descriptions):
    python benchmarks/report.py --markdown

    # List all recorded versions:
    python benchmarks/report.py --list-versions
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

RESULTS_FILE = Path(__file__).parent / "results.csv"
CHARTS_DIR = Path(__file__).parent / "charts"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_results() -> list[dict]:
    """Load all rows from results.csv."""
    if not RESULTS_FILE.exists():
        print(f"No results file found at {RESULTS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(RESULTS_FILE, newline="") as f:
        return list(csv.DictReader(f))


def filter_rows(
    rows: list[dict],
    version: str | None = None,
    library: str | None = None,
    group: str | None = None,
) -> list[dict]:
    """Filter rows by version, library, and/or group."""
    out = rows
    if version:
        out = [r for r in out if r["version"] == version]
    if library:
        out = [r for r in out if r["library"] == library]
    if group:
        out = [r for r in out if r["group"] == group]
    return out


def get_versions(rows: list[dict]) -> list[str]:
    """Return sorted unique versions."""
    return sorted({r["version"] for r in rows})


def get_groups(rows: list[dict]) -> list[str]:
    """Return sorted unique groups."""
    return sorted({r["group"] for r in rows if r["group"]})


def latest_version(rows: list[dict], library: str = "las_rs") -> str | None:
    """Return the most recently timestamped version for a library."""
    lib_rows = [r for r in rows if r["library"] == library]
    if not lib_rows:
        return None
    lib_rows.sort(key=lambda r: r["timestamp"], reverse=True)
    return lib_rows[0]["version"]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_time(seconds_str: str) -> str:
    """Format a time value for display."""
    try:
        s = float(seconds_str)
    except (ValueError, TypeError):
        return seconds_str
    if s < 0.001:
        return f"{s * 1_000_000:.0f} µs"
    elif s < 1.0:
        return f"{s * 1_000:.1f} ms"
    else:
        return f"{s:.2f} s"


def _fmt_ops(ops_str: str) -> str:
    try:
        ops = float(ops_str)
    except (ValueError, TypeError):
        return ops_str
    if ops >= 1000:
        return f"{ops:,.0f}"
    elif ops >= 1:
        return f"{ops:.1f}"
    else:
        return f"{ops:.3f}"


def _short_name(benchmark: str) -> str:
    """Strip common prefixes for display."""
    name = benchmark
    for prefix in ("test_las_rs_", "test_lasio_", "test_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name


# ---------------------------------------------------------------------------
# Table printing
# ---------------------------------------------------------------------------


def print_table(rows: list[dict], title: str = "") -> None:
    """Print a formatted ASCII table of benchmark results."""
    if not rows:
        print("  (no results)")
        return

    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}")

    # Group by benchmark group
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["group"] or "(ungrouped)"].append(r)

    for group_name in sorted(groups):
        group_rows = groups[group_name]
        print(f"\n  [{group_name}]")
        print(f"  {'Benchmark':<45s} {'Mean':>10s} {'Median':>10s} {'Min':>10s} {'Ops/s':>10s} {'Rounds':>7s}")
        print(f"  {'-' * 45} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 7}")

        for r in sorted(group_rows, key=lambda x: x["benchmark"]):
            name = _short_name(r["benchmark"])
            print(
                f"  {name:<45s} "
                f"{_fmt_time(r['mean_s']):>10s} "
                f"{_fmt_time(r['median_s']):>10s} "
                f"{_fmt_time(r['min_s']):>10s} "
                f"{_fmt_ops(r['ops']):>10s} "
                f"{r['rounds']:>7s}"
            )


def print_comparison(
    rows_a: list[dict],
    rows_b: list[dict],
    label_a: str,
    label_b: str,
) -> None:
    """Print a side-by-side comparison table with speedup ratios."""
    # Index by benchmark name
    index_a = {r["benchmark"]: r for r in rows_a}
    index_b = {r["benchmark"]: r for r in rows_b}

    # For las_rs vs lasio comparison, match by stripping library prefix
    if not (set(index_a) & set(index_b)):
        # Try matching by stripped name
        stripped_a = {}
        for name, r in index_a.items():
            key = _short_name(name)
            stripped_a[key] = r
        stripped_b = {}
        for name, r in index_b.items():
            key = _short_name(name)
            stripped_b[key] = r
        common = sorted(set(stripped_a) & set(stripped_b))
        pairs = [(stripped_a[k], stripped_b[k]) for k in common]
    else:
        common_names = sorted(set(index_a) & set(index_b))
        pairs = [(index_a[n], index_b[n]) for n in common_names]

    if not pairs:
        print("  No matching benchmarks found for comparison.")
        return

    print(f"\n{'=' * 100}")
    print(f"  Comparison: {label_a} vs {label_b}")
    print(f"{'=' * 100}")
    print(
        f"  {'Benchmark':<40s} "
        f"{label_a + ' mean':>12s} "
        f"{label_b + ' mean':>12s} "
        f"{'Speedup':>10s} "
        f"{'Winner':>8s}"
    )
    print(f"  {'-' * 40} {'-' * 12} {'-' * 12} {'-' * 10} {'-' * 8}")

    for ra, rb in pairs:
        name = _short_name(ra["benchmark"])
        try:
            mean_a = float(ra["mean_s"])
            mean_b = float(rb["mean_s"])
            if mean_b > 0 and mean_a > 0:
                ratio = mean_b / mean_a
                if ratio >= 1:
                    speedup = f"{ratio:.1f}x"
                    winner = label_a
                else:
                    speedup = f"{1 / ratio:.1f}x"
                    winner = label_b
            else:
                speedup = "N/A"
                winner = ""
        except (ValueError, ZeroDivisionError):
            speedup = "N/A"
            winner = ""

        print(
            f"  {name:<40s} "
            f"{_fmt_time(ra['mean_s']):>12s} "
            f"{_fmt_time(rb['mean_s']):>12s} "
            f"{speedup:>10s} "
            f"{winner:>8s}"
        )


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def print_markdown(rows: list[dict], title: str = "Benchmark Results") -> None:
    """Print results as a GitHub-flavored markdown table."""
    print(f"## {title}\n")

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["group"] or "(ungrouped)"].append(r)

    for group_name in sorted(groups):
        group_rows = groups[group_name]
        print(f"### {group_name}\n")
        print(f"| Benchmark | Mean | Median | Min | Ops/s |")
        print(f"|-----------|------|--------|-----|-------|")
        for r in sorted(group_rows, key=lambda x: x["benchmark"]):
            name = _short_name(r["benchmark"])
            print(
                f"| {name} "
                f"| {_fmt_time(r['mean_s'])} "
                f"| {_fmt_time(r['median_s'])} "
                f"| {_fmt_time(r['min_s'])} "
                f"| {_fmt_ops(r['ops'])} |"
            )
        print()


def print_markdown_comparison(
    rows_a: list[dict],
    rows_b: list[dict],
    label_a: str,
    label_b: str,
) -> None:
    """Print a comparison as a markdown table."""
    index_a = {_short_name(r["benchmark"]): r for r in rows_a}
    index_b = {_short_name(r["benchmark"]): r for r in rows_b}
    common = sorted(set(index_a) & set(index_b))

    if not common:
        print("No matching benchmarks.")
        return

    print(f"## {label_a} vs {label_b}\n")
    print(f"| Benchmark | {label_a} | {label_b} | Speedup |")
    print(f"|-----------|--------|--------|---------|")

    for name in common:
        ra, rb = index_a[name], index_b[name]
        try:
            mean_a = float(ra["mean_s"])
            mean_b = float(rb["mean_s"])
            ratio = mean_b / mean_a if mean_a > 0 else 0
            speedup = f"**{ratio:.1f}x**" if ratio >= 1 else f"{1/ratio:.1f}x slower"
        except (ValueError, ZeroDivisionError):
            speedup = "N/A"

        print(
            f"| {name} "
            f"| {_fmt_time(ra['mean_s'])} "
            f"| {_fmt_time(rb['mean_s'])} "
            f"| {speedup} |"
        )
    print()


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------


def generate_charts(
    rows: list[dict],
    title: str = "",
    output_dir: Path | None = None,
) -> None:
    """Generate PNG bar charts grouped by benchmark group."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — skipping chart generation.", file=sys.stderr)
        print("Install with: pip install matplotlib", file=sys.stderr)
        return

    out = output_dir or CHARTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["group"] or "ungrouped"].append(r)

    for group_name, group_rows in sorted(groups.items()):
        group_rows.sort(key=lambda x: float(x["mean_s"]), reverse=True)
        names = [_short_name(r["benchmark"]) for r in group_rows]
        means = [float(r["mean_s"]) * 1000 for r in group_rows]  # convert to ms

        fig, ax = plt.subplots(figsize=(max(8, len(names) * 0.6), 5))
        bars = ax.barh(names, means, color="#4A90D9")
        ax.set_xlabel("Mean time (ms)")
        ax.set_title(f"{title + ' — ' if title else ''}{group_name}")
        ax.invert_yaxis()

        # Add value labels
        for bar, val in zip(bars, means):
            if val < 1:
                label = f"{val * 1000:.0f} µs"
            elif val < 1000:
                label = f"{val:.1f} ms"
            else:
                label = f"{val / 1000:.2f} s"
            ax.text(bar.get_width() + max(means) * 0.01, bar.get_y() + bar.get_height() / 2,
                    label, va="center", fontsize=8)

        plt.tight_layout()
        filename = group_name.replace(" ", "_").replace("-", "_")
        chart_path = out / f"{filename}.png"
        fig.savefig(chart_path, dpi=150)
        plt.close(fig)
        print(f"  Saved {chart_path}")


def generate_comparison_charts(
    rows_a: list[dict],
    rows_b: list[dict],
    label_a: str,
    label_b: str,
    output_dir: Path | None = None,
) -> None:
    """Generate side-by-side bar charts comparing two result sets."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not installed — skipping chart generation.", file=sys.stderr)
        return

    out = output_dir or CHARTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    index_a = {_short_name(r["benchmark"]): r for r in rows_a}
    index_b = {_short_name(r["benchmark"]): r for r in rows_b}
    common = sorted(set(index_a) & set(index_b))

    if not common:
        print("No matching benchmarks for comparison charts.")
        return

    # Group the common benchmarks
    grouped: dict[str, list[str]] = defaultdict(list)
    for name in common:
        group = index_a[name].get("group", "ungrouped")
        grouped[group].append(name)

    for group_name, names in sorted(grouped.items()):
        means_a = [float(index_a[n]["mean_s"]) * 1000 for n in names]
        means_b = [float(index_b[n]["mean_s"]) * 1000 for n in names]

        x = np.arange(len(names))
        width = 0.35

        fig, ax = plt.subplots(figsize=(max(8, len(names) * 0.8), 5))
        ax.barh(x - width / 2, means_a, width, label=label_a, color="#4A90D9")
        ax.barh(x + width / 2, means_b, width, label=label_b, color="#E8524A")

        ax.set_xlabel("Mean time (ms)")
        ax.set_title(f"{group_name}")
        ax.set_yticks(x)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.legend()

        plt.tight_layout()
        filename = f"compare_{group_name}".replace(" ", "_").replace("-", "_")
        chart_path = out / f"{filename}.png"
        fig.savefig(chart_path, dpi=150)
        plt.close(fig)
        print(f"  Saved {chart_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Report on benchmark results")
    parser.add_argument("--version", default=None, help="Show results for this version")
    parser.add_argument("--group", default=None, help="Filter to this benchmark group")
    parser.add_argument("--compare", nargs=2, metavar=("V1", "V2"), help="Compare two versions")
    parser.add_argument("--vs-lasio", metavar="VERSION", help="Compare las_rs VERSION vs lasio")
    parser.add_argument("--charts", action="store_true", help="Generate PNG charts")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown")
    parser.add_argument("--list-versions", action="store_true", help="List all recorded versions")
    parser.add_argument("--list-groups", action="store_true", help="List all benchmark groups")
    args = parser.parse_args()

    rows = load_results()
    if not rows:
        print("No results in results.csv")
        return

    # List modes
    if args.list_versions:
        for v in get_versions(rows):
            lib_rows = [r for r in rows if r["version"] == v]
            libs = sorted({r["library"] for r in lib_rows})
            count = len(lib_rows)
            print(f"  {v:20s}  {', '.join(libs):15s}  {count} benchmarks")
        return

    if args.list_groups:
        for g in get_groups(rows):
            count = len([r for r in rows if r["group"] == g])
            print(f"  {g:30s}  {count} results")
        return

    # Comparison: two versions
    if args.compare:
        v1, v2 = args.compare
        rows_a = filter_rows(rows, version=v1, library="las_rs", group=args.group)
        rows_b = filter_rows(rows, version=v2, library="las_rs", group=args.group)

        if args.markdown:
            print_markdown_comparison(rows_a, rows_b, f"las_rs {v1}", f"las_rs {v2}")
        else:
            print_comparison(rows_a, rows_b, f"las_rs {v1}", f"las_rs {v2}")

        if args.charts:
            generate_comparison_charts(rows_a, rows_b, f"las_rs {v1}", f"las_rs {v2}")
        return

    # Comparison: las_rs vs lasio
    if args.vs_lasio:
        v = args.vs_lasio
        rows_a = filter_rows(rows, version=v, library="las_rs", group=args.group)
        rows_b = filter_rows(rows, version=v, library="lasio", group=args.group)

        if args.markdown:
            print_markdown_comparison(rows_a, rows_b, f"las_rs {v}", "lasio")
        else:
            print_comparison(rows_a, rows_b, f"las_rs {v}", "lasio")

        if args.charts:
            generate_comparison_charts(rows_a, rows_b, f"las_rs {v}", "lasio")
        return

    # Single version display
    version = args.version or latest_version(rows)
    if version:
        filtered = filter_rows(rows, version=version, group=args.group)
    else:
        filtered = filter_rows(rows, group=args.group)

    if not filtered:
        print(f"No results found for version={version}, group={args.group}")
        return

    title = f"las_rs {version}" if version else "All results"

    if args.markdown:
        print_markdown(filtered, title)
    else:
        print_table(filtered, title)

    if args.charts:
        generate_charts(filtered, title)


if __name__ == "__main__":
    main()
