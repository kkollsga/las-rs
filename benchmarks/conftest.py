"""Shared fixtures for benchmark tests.

Size tiers for ~2min target on tier1+tier2:
  tiny:    100 rows × 4 curves   (~3 KB)   — overhead measurement
  small:   1K rows × 8 curves    (~80 KB)  — fast iteration
  medium:  10K rows × 8 curves   (~760 KB) — tier2 workhorse
  large:   100K rows × 8 curves  (~7.6 MB) — tier3 only
  huge:    1M rows × 8 curves    (~76 MB)  — tier3 only
  wide:    10K rows × 200 curves (~16 MB)  — tier3 only
"""

from __future__ import annotations

import pytest
from pathlib import Path
from benchmarks.generate import Generator, generate_matrix


@pytest.fixture(scope="session")
def gen() -> Generator:
    return Generator(seed=42)


@pytest.fixture(scope="session")
def batch_files(gen) -> list[Path]:
    """100 small files for batch benchmarks (tier3 uses 500)."""
    return gen.make_batch(count=100, rows=1_000, curves=8)


# ---------------------------------------------------------------------------
# Size fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tiny_file(gen) -> Path:
    """100 rows × 4 curves."""
    return gen.make(rows=100, curves=4)


@pytest.fixture(scope="session")
def small_file(gen) -> Path:
    """1K rows × 8 curves."""
    return gen.make(rows=1_000, curves=8)


@pytest.fixture(scope="session")
def medium_file(gen) -> Path:
    """10K rows × 8 curves — the tier2 workhorse."""
    return gen.make(rows=10_000, curves=8)


@pytest.fixture(scope="session")
def large_file(gen) -> Path:
    """100K rows × 8 curves — tier3 only."""
    return gen.make(rows=100_000, curves=8)


@pytest.fixture(scope="session")
def huge_file(gen) -> Path:
    """1M rows × 8 curves — tier3 only."""
    return gen.make(rows=1_000_000, curves=8)


@pytest.fixture(scope="session")
def wide_file(gen) -> Path:
    """10K rows × 200 curves — tier3 only."""
    return gen.make(rows=10_000, curves=200)


@pytest.fixture(scope="session")
def wrapped_file(gen) -> Path:
    """10K rows × 30 curves, WRAP=YES."""
    return gen.make(rows=10_000, curves=30, wrap=True)


@pytest.fixture(scope="session")
def nulls_heavy_file(gen) -> Path:
    """10K rows × 8 curves, 30% nulls."""
    return gen.make(rows=10_000, curves=8, null_fraction=0.30)
