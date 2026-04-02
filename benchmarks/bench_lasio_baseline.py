"""Baseline benchmarks: lasio performance on synthetic files.

Run BEFORE las_rs exists to establish the performance target.
Tier1+tier2 completes in ~2 minutes. Tier3 adds large/wide/batch tests.

Run:
    pytest benchmarks/bench_lasio_baseline.py -m "tier1 or tier2" --benchmark-only -v
    pytest benchmarks/bench_lasio_baseline.py --benchmark-only -v   # all tiers
"""

from __future__ import annotations

from io import StringIO

import pytest
import lasio


def _load(path):
    return lasio.read(str(path))


# ===================================================================
# TIER 1 — tiny/small, fast ops (~30s)
# ===================================================================


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-scaling")
def test_read_tiny(benchmark, tiny_file):
    """100 × 4."""
    benchmark(lasio.read, str(tiny_file))


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-scaling")
def test_read_small(benchmark, small_file):
    """1K × 8."""
    benchmark(lasio.read, str(small_file))


@pytest.mark.tier1
@pytest.mark.benchmark(group="write")
def test_write_small(benchmark, small_file):
    """Write 1K × 8."""
    las = _load(small_file)
    benchmark(lambda: las.write(StringIO()))


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_getitem_mnemonic(benchmark, small_file):
    """las['GR'] lookup."""
    las = _load(small_file)
    benchmark(lambda: las["GR"])


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_getitem_index(benchmark, small_file):
    """las[1] lookup."""
    las = _load(small_file)
    benchmark(lambda: las[1])


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_index_property(benchmark, small_file):
    """las.index."""
    las = _load(small_file)
    benchmark(lambda: las.index)


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_data_property(benchmark, small_file):
    """las.data (vstack)."""
    las = _load(small_file)
    benchmark(lambda: las.data)


@pytest.mark.tier1
@pytest.mark.benchmark(group="export-json")
def test_json_small(benchmark, small_file):
    """JSON 1K × 8."""
    las = _load(small_file)
    benchmark(lambda: las.json)


@pytest.mark.tier1
@pytest.mark.benchmark(group="read-header-only")
def test_header_only_small(benchmark, small_file):
    """Header-only read, 1K file."""
    benchmark(lasio.read, str(small_file), ignore_data=True)


# ===================================================================
# TIER 2 — medium (10K rows), features (~90s)
# ===================================================================


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-scaling")
def test_read_medium(benchmark, medium_file):
    """10K × 8."""
    benchmark(lasio.read, str(medium_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-engine")
def test_engine_numpy(benchmark, medium_file):
    """numpy engine, 10K × 8."""
    benchmark(lasio.read, str(medium_file), engine="numpy")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-engine")
def test_engine_normal(benchmark, medium_file):
    """normal engine, 10K × 8."""
    benchmark(lasio.read, str(medium_file), engine="normal")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-nulls")
def test_read_no_nulls(benchmark, medium_file):
    """10K, 0% nulls."""
    benchmark(lasio.read, str(medium_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-nulls")
def test_read_nulls_heavy(benchmark, nulls_heavy_file):
    """10K, 30% nulls."""
    benchmark(lasio.read, str(nulls_heavy_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-null-policy")
def test_null_policy_strict(benchmark, nulls_heavy_file):
    benchmark(lasio.read, str(nulls_heavy_file), null_policy="strict")


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-null-policy")
def test_null_policy_none(benchmark, nulls_heavy_file):
    benchmark(lasio.read, str(nulls_heavy_file), null_policy="none")


@pytest.mark.tier2
@pytest.mark.benchmark(group="write")
def test_write_medium(benchmark, medium_file):
    """Write 10K × 8."""
    las = _load(medium_file)
    benchmark(lambda: las.write(StringIO()))


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-wrapped")
def test_read_wrapped(benchmark, wrapped_file):
    """10K × 30, wrapped."""
    benchmark(lasio.read, str(wrapped_file))


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-df")
def test_df_medium(benchmark, medium_file):
    """DataFrame 10K × 8."""
    las = _load(medium_file)
    benchmark(las.df)


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-csv")
def test_csv_small(benchmark, small_file):
    """CSV 1K × 8."""
    las = _load(small_file)
    benchmark(lambda: las.to_csv(StringIO()))


@pytest.mark.tier2
@pytest.mark.benchmark(group="export-json")
def test_json_medium(benchmark, medium_file):
    """JSON 10K × 8."""
    las = _load(medium_file)
    benchmark(lambda: las.json)


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-roundtrip")
def test_roundtrip_small(benchmark, small_file):
    """Read+write 1K × 8."""
    def go():
        las = lasio.read(str(small_file))
        las.write(StringIO())
    benchmark(go)


@pytest.mark.tier2
@pytest.mark.benchmark(group="read-header-only")
def test_header_only_medium(benchmark, medium_file):
    """Header-only, 10K file."""
    benchmark(lasio.read, str(medium_file), ignore_data=True)


# ===================================================================
# TIER 3 — large/wide/batch (100K+ rows, minutes)
# ===================================================================


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-scaling")
def test_read_large(benchmark, large_file):
    """100K × 8."""
    benchmark(lasio.read, str(large_file))


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-scaling")
def test_read_huge(benchmark, huge_file):
    """1M × 8."""
    benchmark(lasio.read, str(huge_file))


@pytest.mark.tier3
@pytest.mark.benchmark(group="read-scaling")
def test_read_wide(benchmark, wide_file):
    """10K × 200."""
    benchmark(lasio.read, str(wide_file))


@pytest.mark.tier3
@pytest.mark.benchmark(group="write")
def test_write_large(benchmark, large_file):
    """Write 100K × 8."""
    las = _load(large_file)
    benchmark(lambda: las.write(StringIO()))


@pytest.mark.tier3
@pytest.mark.benchmark(group="write")
def test_write_wide(benchmark, wide_file):
    """Write 10K × 200."""
    las = _load(wide_file)
    benchmark(lambda: las.write(StringIO()))


@pytest.mark.tier3
@pytest.mark.benchmark(group="export-df")
def test_df_large(benchmark, large_file):
    """DataFrame 100K × 8."""
    las = _load(large_file)
    benchmark(las.df)


@pytest.mark.tier3
@pytest.mark.benchmark(group="export-csv")
def test_csv_medium(benchmark, medium_file):
    """CSV 10K × 8."""
    las = _load(medium_file)
    benchmark(lambda: las.to_csv(StringIO()))


@pytest.mark.tier3
@pytest.mark.benchmark(group="ops-roundtrip")
def test_roundtrip_medium(benchmark, medium_file):
    """Read+write 10K × 8."""
    def go():
        las = lasio.read(str(medium_file))
        las.write(StringIO())
    benchmark(go)
