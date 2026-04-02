"""Head-to-head benchmarks: las_rs vs lasio on identical files.

Run with: pytest benchmarks/bench_compare.py --benchmark-only -v

Both libraries read/write the exact same generated files so timing
comparisons are apples-to-apples.  If lasio is not installed the
lasio benchmarks are skipped automatically.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Conditional imports
# ---------------------------------------------------------------------------

import las_rs

try:
    import lasio

    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False

skip_no_lasio = pytest.mark.skipif(not HAS_LASIO, reason="lasio not installed")


# ===================================================================
# READ BENCHMARKS
# ===================================================================


# --- Small (1K × 8) ---


@pytest.mark.tier1
@pytest.mark.benchmark(group="compare-read-small")
def test_las_rs_read_small(benchmark, small_file):
    benchmark(las_rs.read, str(small_file))


@skip_no_lasio
@pytest.mark.tier1
@pytest.mark.benchmark(group="compare-read-small")
def test_lasio_read_small(benchmark, small_file):
    benchmark(lasio.read, str(small_file))


# --- Medium (100K × 8) ---


@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-read-medium")
def test_las_rs_read_medium(benchmark, medium_file):
    benchmark(las_rs.read, str(medium_file))


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-read-medium")
def test_lasio_read_medium(benchmark, medium_file):
    benchmark(lasio.read, str(medium_file))


# --- Large (1M × 8) ---


@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-large")
def test_las_rs_read_large(benchmark, large_file):
    benchmark(las_rs.read, str(large_file))


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-large")
def test_lasio_read_large(benchmark, large_file):
    benchmark(lasio.read, str(large_file))


# --- Wide (10K × 200) ---


@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-wide")
def test_las_rs_read_wide(benchmark, wide_file):
    benchmark(las_rs.read, str(wide_file))


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-wide")
def test_lasio_read_wide(benchmark, wide_file):
    benchmark(lasio.read, str(wide_file))


# --- Wrapped (100K × 30) ---


@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-wrapped")
def test_las_rs_read_wrapped(benchmark, wrapped_file):
    benchmark(las_rs.read, str(wrapped_file))


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-read-wrapped")
def test_lasio_read_wrapped(benchmark, wrapped_file):
    benchmark(lasio.read, str(wrapped_file))


# --- Nulls heavy (100K × 8, 30% nulls) ---


@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-read-nulls")
def test_las_rs_read_nulls(benchmark, nulls_heavy_file):
    benchmark(las_rs.read, str(nulls_heavy_file))


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-read-nulls")
def test_lasio_read_nulls(benchmark, nulls_heavy_file):
    benchmark(lasio.read, str(nulls_heavy_file))


# --- Header-only (100K × 8, ignore_data) ---


@pytest.mark.tier1
@pytest.mark.benchmark(group="compare-read-header-only")
def test_las_rs_header_only(benchmark, medium_file):
    benchmark(las_rs.read, str(medium_file), ignore_data=True)


@skip_no_lasio
@pytest.mark.tier1
@pytest.mark.benchmark(group="compare-read-header-only")
def test_lasio_header_only(benchmark, medium_file):
    benchmark(lasio.read, str(medium_file), ignore_data=True)


# ===================================================================
# WRITE BENCHMARKS
# ===================================================================


@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-write-medium")
def test_las_rs_write_medium(benchmark, medium_file):
    las = las_rs.read(str(medium_file))

    def go():
        s = StringIO()
        las.write(s)

    benchmark(go)


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-write-medium")
def test_lasio_write_medium(benchmark, medium_file):
    las = lasio.read(str(medium_file))

    def go():
        s = StringIO()
        las.write(s)

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-write-large")
def test_las_rs_write_large(benchmark, large_file):
    las = las_rs.read(str(large_file))

    def go():
        s = StringIO()
        las.write(s)

    benchmark(go)


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-write-large")
def test_lasio_write_large(benchmark, large_file):
    las = lasio.read(str(large_file))

    def go():
        s = StringIO()
        las.write(s)

    benchmark(go)


# ===================================================================
# DATAFRAME BENCHMARKS
# ===================================================================


@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-df-medium")
def test_las_rs_df_medium(benchmark, medium_file):
    las = las_rs.read(str(medium_file))
    benchmark(las.df)


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-df-medium")
def test_lasio_df_medium(benchmark, medium_file):
    las = lasio.read(str(medium_file))
    benchmark(las.df)


@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-df-large")
def test_las_rs_df_large(benchmark, large_file):
    las = las_rs.read(str(large_file))
    benchmark(las.df)


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="compare-df-large")
def test_lasio_df_large(benchmark, large_file):
    las = lasio.read(str(large_file))
    benchmark(las.df)


# ===================================================================
# ROUND-TRIP BENCHMARKS
# ===================================================================


@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-roundtrip")
def test_las_rs_roundtrip(benchmark, medium_file):
    def go():
        las = las_rs.read(str(medium_file))
        s = StringIO()
        las.write(s)
        s.seek(0)
        las2 = las_rs.read(s.read())
        return las2

    benchmark(go)


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="compare-roundtrip")
def test_lasio_roundtrip(benchmark, medium_file):
    def go():
        las = lasio.read(str(medium_file))
        s = StringIO()
        las.write(s)
        s.seek(0)
        las2 = lasio.read(s.read())
        return las2

    benchmark(go)
