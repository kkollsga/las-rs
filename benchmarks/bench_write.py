"""Benchmarks: LAS file writing performance.

Covers write speed, CSV export, JSON export, and DataFrame conversion.
Run with: pytest benchmarks/bench_write.py --benchmark-only -v
"""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> las_rs.LASFile:
    """Read a LAS file once (not part of the timed benchmark)."""
    return las_rs.read(str(path))


# ---------------------------------------------------------------------------
# Write to StringIO (in-memory)
# ---------------------------------------------------------------------------


@pytest.mark.tier1
@pytest.mark.benchmark(group="write-memory")
def test_write_small(benchmark, small_file):
    """Write 1K × 8 to StringIO."""
    las = _load(small_file)

    def go():
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)


@pytest.mark.tier2
@pytest.mark.benchmark(group="write-memory")
def test_write_medium(benchmark, medium_file):
    """Write 100K × 8 to StringIO."""
    las = _load(medium_file)

    def go():
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="write-memory")
def test_write_large(benchmark, large_file):
    """Write 1M × 8 to StringIO."""
    las = _load(large_file)

    def go():
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="write-memory")
def test_write_wide(benchmark, wide_file):
    """Write 10K × 200 to StringIO."""
    las = _load(wide_file)

    def go():
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)


# ---------------------------------------------------------------------------
# Write to disk
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="write-disk")
def test_write_medium_disk(benchmark, medium_file, tmp_path):
    """Write 100K × 8 to a temp file on disk."""
    las = _load(medium_file)
    out = tmp_path / "bench_write.las"

    def go():
        las.write(str(out))

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="write-disk")
def test_write_large_disk(benchmark, large_file, tmp_path):
    """Write 1M × 8 to a temp file on disk."""
    las = _load(large_file)
    out = tmp_path / "bench_write_large.las"

    def go():
        las.write(str(out))

    benchmark(go)


# ---------------------------------------------------------------------------
# Write wrapped
# ---------------------------------------------------------------------------


@pytest.mark.tier3
@pytest.mark.benchmark(group="write-wrapped")
def test_write_wrapped(benchmark, wrapped_file):
    """Write 100K × 30 as wrapped data."""
    las = _load(wrapped_file)

    def go():
        s = StringIO()
        las.write(s, wrap=True)
        return s

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="write-wrapped")
def test_write_unwrapped_same_data(benchmark, wrapped_file):
    """Same file written unwrapped — baseline for wrap overhead."""
    las = _load(wrapped_file)

    def go():
        s = StringIO()
        las.write(s, wrap=False)
        return s

    benchmark(go)


# ---------------------------------------------------------------------------
# Format string performance
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="write-format")
def test_write_fmt_5f(benchmark, medium_file):
    """Default %.5f format."""
    las = _load(medium_file)

    def go():
        s = StringIO()
        las.write(s, fmt="%.5f")
        return s

    benchmark(go)


@pytest.mark.tier2
@pytest.mark.benchmark(group="write-format")
def test_write_fmt_10f(benchmark, medium_file):
    """High-precision %.10f format — longer strings."""
    las = _load(medium_file)

    def go():
        s = StringIO()
        las.write(s, fmt="%.10f")
        return s

    benchmark(go)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-csv")
def test_csv_medium(benchmark, medium_file):
    """CSV export of 100K × 8."""
    las = _load(medium_file)

    def go():
        s = StringIO()
        las.to_csv(s)
        return s

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="export-csv")
def test_csv_large(benchmark, large_file):
    """CSV export of 1M × 8."""
    las = _load(large_file)

    def go():
        s = StringIO()
        las.to_csv(s)
        return s

    benchmark(go)


# ---------------------------------------------------------------------------
# DataFrame conversion
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-df")
def test_df_medium(benchmark, medium_file):
    """las.df() on 100K × 8."""
    las = _load(medium_file)
    benchmark(las.df)


@pytest.mark.tier3
@pytest.mark.benchmark(group="export-df")
def test_df_large(benchmark, large_file):
    """las.df() on 1M × 8."""
    las = _load(large_file)
    benchmark(las.df)


@pytest.mark.tier3
@pytest.mark.benchmark(group="export-df")
def test_df_wide(benchmark, wide_file):
    """las.df() on 10K × 200."""
    las = _load(wide_file)
    benchmark(las.df)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


@pytest.mark.tier1
@pytest.mark.benchmark(group="export-json")
def test_json_small(benchmark, small_file):
    """JSON export of 1K × 8."""
    las = _load(small_file)
    benchmark(lambda: las.json)


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-json")
def test_json_medium(benchmark, medium_file):
    """JSON export of 100K × 8."""
    las = _load(medium_file)
    benchmark(lambda: las.json)
