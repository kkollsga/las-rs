"""Benchmarks: In-memory operations on LASFile objects.

Covers curve manipulation, data access patterns, and property lookups.
Run with: pytest benchmarks/bench_ops.py --benchmark-only -v
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import numpy as np
import pytest

import las_rs


def _load(path: Path) -> las_rs.LASFile:
    return las_rs.read(str(path))


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-access")
def test_access_data_property(benchmark, medium_file):
    """Accessing las.data (builds 2D array from curve columns) — 100K × 8."""
    las = _load(medium_file)
    benchmark(lambda: las.data)


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_access_index_property(benchmark, large_file):
    """Accessing las.index (first curve data) — 1M rows."""
    las = _load(large_file)
    benchmark(lambda: las.index)


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_access_getitem_by_mnemonic(benchmark, medium_file):
    """las['GR'] lookup by mnemonic — 100K rows."""
    las = _load(medium_file)
    benchmark(lambda: las["GR"])


@pytest.mark.tier1
@pytest.mark.benchmark(group="ops-access")
def test_access_getitem_by_index(benchmark, medium_file):
    """las[1] lookup by integer index — 100K rows."""
    las = _load(medium_file)
    benchmark(lambda: las[1])


# ---------------------------------------------------------------------------
# Curve manipulation
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-curve-manip")
def test_append_curve(benchmark, small_file):
    """Append a new curve to a 1K × 8 file."""
    las_orig = _load(small_file)
    new_data = np.random.default_rng(99).standard_normal(1_000) * 10 + 50

    def go():
        # Work on a fresh copy each iteration to avoid accumulation.
        las = las_rs.read(str(small_file))
        las.append_curve("BENCH", new_data, unit="GAPI", descr="Benchmark curve")
        return las

    benchmark(go)


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-curve-manip")
def test_delete_curve(benchmark, small_file):
    """Delete a curve from a 1K × 8 file."""

    def go():
        las = las_rs.read(str(small_file))
        las.delete_curve(mnemonic="GR")
        return las

    benchmark(go)


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-curve-manip")
def test_set_data_from_array(benchmark, medium_file):
    """las.set_data(array) on a 100K × 8 file."""
    las = _load(medium_file)
    data = las.data.copy()

    def go():
        las.set_data(data)

    benchmark(go)


# ---------------------------------------------------------------------------
# Stack curves
# ---------------------------------------------------------------------------


_STACK_LAS = """\
~VERSION INFORMATION
 VERS. 2.0 : CWLS LOG ASCII STANDARD -VERSION 2.0
 WRAP.  NO : One line per depth step
~WELL INFORMATION
 STRT.M 0.0 : START
 STOP.M 4.0 : STOP
 STEP.M 1.0 : STEP
 NULL.  -999.25 : NULL
 WELL.  STACK-BENCH : WELL
~CURVE INFORMATION
 DEPT.M    : Depth
 GR  .GAPI : Gamma Ray
"""


def _make_stack_las(n_channels: int, n_rows: int) -> str:
    """Build a LAS string with n_channels multichannel curves."""
    lines = [_STACK_LAS.rstrip()]
    for i in range(1, n_channels + 1):
        lines.append(f" TRC{i:03d}.NONE : Trace channel {i}")
    lines.append("~ASCII")
    rng = np.random.default_rng(77)
    for r in range(n_rows):
        depth = r * 0.1524
        gr = rng.normal(60, 15)
        vals = " ".join(f"{rng.normal(0, 1):.4f}" for _ in range(n_channels))
        lines.append(f" {depth:.4f} {gr:.4f} {vals}")
    return "\n".join(lines) + "\n"


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-stack")
def test_stack_10_channels(benchmark):
    """stack_curves on 10 channels × 10K rows."""
    content = _make_stack_las(10, 10_000)
    las = las_rs.read(content)
    benchmark(las.stack_curves, "TRC")


@pytest.mark.tier3
@pytest.mark.benchmark(group="ops-stack")
def test_stack_100_channels(benchmark):
    """stack_curves on 100 channels × 10K rows."""
    content = _make_stack_las(100, 10_000)
    las = las_rs.read(content)
    benchmark(las.stack_curves, "TRC")


# ---------------------------------------------------------------------------
# Round-trip: read → modify → write
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="ops-roundtrip")
def test_roundtrip_medium(benchmark, medium_file):
    """Full read → write cycle on 100K × 8."""

    def go():
        las = las_rs.read(str(medium_file))
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)


@pytest.mark.tier3
@pytest.mark.benchmark(group="ops-roundtrip")
def test_roundtrip_wide(benchmark, wide_file):
    """Full read → write cycle on 10K × 200."""

    def go():
        las = las_rs.read(str(wide_file))
        s = StringIO()
        las.write(s)
        return s

    benchmark(go)
