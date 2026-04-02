"""Benchmarks: LAS file reading performance.

Covers the core read path across file sizes, widths, engines, and features.
Run with: pytest benchmarks/bench_read.py --benchmark-only -v

These benchmarks target las_rs.  For head-to-head comparison with lasio,
see bench_compare.py.
"""

from __future__ import annotations

import pytest

import las_rs

# ---------------------------------------------------------------------------
# Scaling: rows
# ---------------------------------------------------------------------------


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-scaling-rows")
def test_read_tiny(benchmark, tiny_file):
    """100 rows × 4 curves — baseline overhead."""
    benchmark(las_rs.read, str(tiny_file))


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-scaling-rows")
def test_read_small(benchmark, small_file):
    """1K rows × 8 curves."""
    benchmark(las_rs.read, str(small_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-scaling-rows")
def test_read_medium(benchmark, medium_file):
    """100K rows × 8 curves — typical production file."""
    benchmark(las_rs.read, str(medium_file))


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-scaling-rows")
def test_read_large(benchmark, large_file):
    """1M rows × 8 curves — large wellbore."""
    benchmark(las_rs.read, str(large_file))


# ---------------------------------------------------------------------------
# Scaling: columns (wide files)
# ---------------------------------------------------------------------------


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-scaling-cols")
def test_read_wide(benchmark, wide_file):
    """10K rows × 200 curves — image log / array sonic width."""
    benchmark(las_rs.read, str(wide_file))


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-scaling-cols")
def test_read_narrow(benchmark, small_file):
    """1K rows × 8 curves — narrow baseline for comparison."""
    benchmark(las_rs.read, str(small_file))


# ---------------------------------------------------------------------------
# Features: wrapped data
# ---------------------------------------------------------------------------


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-features")
def test_read_wrapped(benchmark, wrapped_file):
    """100K rows × 30 curves, WRAP=YES."""
    benchmark(las_rs.read, str(wrapped_file))


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-features")
def test_read_unwrapped_same_size(benchmark, medium_file):
    """100K rows × 8 curves, WRAP=NO — baseline for wrapped comparison."""
    benchmark(las_rs.read, str(medium_file))


# ---------------------------------------------------------------------------
# Features: null replacement
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-nulls")
def test_read_no_nulls(benchmark, medium_file):
    """100K rows, 0% nulls."""
    benchmark(las_rs.read, str(medium_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-nulls")
def test_read_nulls_heavy(benchmark, nulls_heavy_file):
    """100K rows, 30% null values — measures regex substitution overhead."""
    benchmark(las_rs.read, str(nulls_heavy_file))


# ---------------------------------------------------------------------------
# Features: null policies
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-null-policy")
def test_read_null_policy_strict(benchmark, nulls_heavy_file):
    """strict policy — only header NULL value."""
    benchmark(las_rs.read, str(nulls_heavy_file), null_policy="strict")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-null-policy")
def test_read_null_policy_none(benchmark, nulls_heavy_file):
    """none policy — skip all null processing."""
    benchmark(las_rs.read, str(nulls_heavy_file), null_policy="none")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-null-policy")
def test_read_null_policy_aggressive(benchmark, nulls_heavy_file):
    """aggressive policy — maximum regex work."""
    benchmark(las_rs.read, str(nulls_heavy_file), null_policy="aggressive")


# ---------------------------------------------------------------------------
# Engine comparison
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-engine")
def test_read_engine_numpy(benchmark, medium_file):
    """numpy engine on 100K rows."""
    benchmark(las_rs.read, str(medium_file), engine="numpy")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-engine")
def test_read_engine_normal(benchmark, medium_file):
    """normal (pure Python/Rust) engine on 100K rows."""
    benchmark(las_rs.read, str(medium_file), engine="normal")


# ---------------------------------------------------------------------------
# Header-only read (ignore_data=True)
# ---------------------------------------------------------------------------


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-header-only")
def test_read_header_only_medium(benchmark, medium_file):
    """Read only headers from a 100K-row file — measures header parsing speed."""
    benchmark(las_rs.read, str(medium_file), ignore_data=True)


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-header-only")
def test_read_header_only_large(benchmark, large_file):
    """Read only headers from a 1M-row file — should be near-instant."""
    benchmark(las_rs.read, str(large_file), ignore_data=True)
