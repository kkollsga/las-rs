"""
Phase 3 tests — Wrapped data mode.

Covers WRAP flag detection, correct data point counting, the constraint that
wrapped files always use the normal engine, and round-trip read/write
correctness for wrapped files.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
from io import StringIO

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    return os.path.join(test_dir, "fixtures", fn)


WRAPPED_V12 = fixture("v12/sample_v12_wrapped.las")
WRAPPED_V20 = fixture("v20/sample_v20_wrapped.las")


# ---------------------------------------------------------------------------
# WRAP flag detection
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_flag_detected():
    """Reading a WRAP=YES file sets the version section WRAP item's value
    to 'YES'."""
    las = las_rs.read(WRAPPED_V12)
    assert las.version["WRAP"].value.strip().upper() == "YES"


# ---------------------------------------------------------------------------
# Data point count
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_data_count():
    """The wrapped v1.2 fixture has 4 depth steps and 12 curves (DEPT + 11
    measurement channels).  Total data points = 4 × 12 = 48."""
    las = las_rs.read(WRAPPED_V12)
    assert las.data.size == 4 * 12


# ---------------------------------------------------------------------------
# Engine constraint
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_uses_normal_engine():
    """Requesting engine='numpy' on a wrapped file silently falls back to
    the normal engine (data is still correctly parsed)."""
    las_normal = las_rs.read(WRAPPED_V12, engine="normal")
    las_numpy_req = las_rs.read(WRAPPED_V12, engine="numpy")
    # Both should produce identical data regardless of the engine request
    np.testing.assert_array_almost_equal(
        las_normal.curves["DEPT"].data,
        las_numpy_req.curves["DEPT"].data,
    )


# ---------------------------------------------------------------------------
# Writing wrapped output
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_wrapped():
    """Writing with wrap=True produces a data section where each depth step
    spans multiple lines."""
    las = las_rs.read(WRAPPED_V12)
    buf = StringIO()
    las.write(buf, wrap=True)
    output = buf.getvalue()
    # In a wrapped file the depth value appears alone on its own line;
    # the first depth (800.0) must be on a line by itself.
    data_section = output[output.index("~A") :]
    lines = [l.strip() for l in data_section.splitlines() if l.strip() and not l.startswith("~")]
    # A wrapped line has far fewer tokens than all curves on one line.
    # At minimum there must be more data lines than depth steps.
    assert len(lines) > 4  # 4 depth steps → must have continuation lines


@pytest.mark.xfail(reason="not yet implemented")
def test_write_unwrapped():
    """Writing with wrap=False puts all values for a single depth step on
    one line."""
    las = las_rs.read(WRAPPED_V12)
    buf = StringIO()
    las.write(buf, wrap=False)
    output = buf.getvalue()
    # Locate the data section
    data_start = output.index("~A")
    data_lines = [
        l for l in output[data_start:].splitlines()
        if l.strip() and not l.strip().startswith("~") and not l.strip().startswith("#")
    ]
    # There should be exactly 4 non-header data lines (one per depth step)
    assert len(data_lines) == 4


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_roundtrip():
    """Read a wrapped file, write it back as wrapped, re-read it, and verify
    that the curve data arrays are numerically identical."""
    original = las_rs.read(WRAPPED_V12)

    buf = StringIO()
    original.write(buf, wrap=True)
    buf.seek(0)

    reread = las_rs.read(buf)

    for curve in original.curves:
        np.testing.assert_array_almost_equal(
            curve.data,
            reread.curves[curve.mnemonic].data,
            decimal=4,
        )
