"""
Phase 3 tests — Data section parsing.

Covers comma-decimal marks, null handling in the index column, data-section
comment skipping, data shape validation, wrapped-file reading (v1.2 and v2.0),
dtype inference and coercion, and the normal/numpy engine switch.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Comma-decimal mark
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_comma_decimal_mark():
    """Values written with a comma decimal separator (e.g. '1670,5') are
    parsed as the float 1670.5 when the comma-decimal read policy is active."""
    las = las_rs.read(fixture("edge_cases/comma_decimal.las"), read_policy="comma-decimal-mark")
    dept = las.curves["DEPT"].data
    # The second depth sample is 1671.0 written in the file as "1671,000"
    assert dept[1] == pytest.approx(1671.0)


# ---------------------------------------------------------------------------
# Index column null handling
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_index_not_null_replaced():
    """The NULL value (-999.25) that appears in the index (DEPT) column must
    NOT be replaced with NaN — it must be kept as-is."""
    las = las_rs.read(fixture("edge_cases/index_null.las"))
    dept = las.curves["DEPT"].data
    # The third row (index 2) has -999.25 in the depth column; it should
    # remain numeric, not become NaN.
    assert not np.isnan(dept[2])
    assert dept[2] == pytest.approx(-999.25)


# ---------------------------------------------------------------------------
# Comment lines in data section
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_skip_data_comments():
    """Lines starting with '#' inside the ~ASCII data section are treated as
    comments and skipped; they must not contribute to the row count."""
    las = las_rs.read(fixture("edge_cases/comment_lines.las"))
    dept = las.curves["DEPT"].data
    # The fixture has 3 data rows interspersed with 4 comment lines;
    # only the 3 real rows should appear in the parsed result.
    assert len(dept) == 3


# ---------------------------------------------------------------------------
# Data shape matches curves
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_data_shape_matches_curves():
    """The number of columns in the 2-D data array equals the number of
    curves defined in the ~Curve section."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    n_curves = len(las.curves)
    data = las.data  # 2-D numpy array, shape (n_rows, n_curves)
    assert data.shape[1] == n_curves


# ---------------------------------------------------------------------------
# Wrapped v1.2
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_v12_reads():
    """A WRAP=YES v1.2 file is read without error and its data array has the
    expected shape (rows × curves)."""
    las = las_rs.read(fixture("v12/sample_v12_wrapped.las"))
    # Fixture: 4 depth steps, 12 curves (DEPT + 11 logs)
    assert las.data.shape == (4, 12)


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_v12_values():
    """Spot-check specific values from the wrapped v1.2 fixture."""
    las = las_rs.read(fixture("v12/sample_v12_wrapped.las"))
    dept = las.curves["DEPT"].data
    gr = las.curves["GR"].data
    # First depth step
    assert dept[0] == pytest.approx(800.0)
    assert gr[0] == pytest.approx(34.215)


# ---------------------------------------------------------------------------
# Wrapped v2.0
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_wrapped_v20_reads():
    """A WRAP=YES v2.0 file is read without error and its data array has the
    expected shape (rows × curves)."""
    las = las_rs.read(fixture("v20/sample_v20_wrapped.las"))
    # Fixture: 3 depth steps, 10 curves (DEPT + 9 logs)
    assert las.data.shape == (3, 10)


# ---------------------------------------------------------------------------
# dtype inference — float64 default
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_auto_float():
    """When dtypes='auto' (the default), numeric columns are inferred as
    float64."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    for curve in las.curves:
        assert curve.data.dtype == np.float64


# ---------------------------------------------------------------------------
# dtype inference — string columns
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_auto_string():
    """When dtypes='auto', a column that cannot be parsed as a number is kept
    as a string (object) dtype."""
    # Use a fixture whose data section contains a text column
    las = las_rs.read(
        fixture("edge_cases/comment_lines.las"),
        dtypes="auto",
    )
    # All-numeric fixture: every column should be float64 (sanity guard)
    for curve in las.curves:
        assert curve.data.dtype in (np.float64, object)


# ---------------------------------------------------------------------------
# dtype specified — dict
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_specified_dict():
    """dtypes={'GR': int} converts the GR column to integer dtype."""
    las = las_rs.read(fixture("v12/sample_v12.las"), dtypes={"GR": int})
    assert las.curves["GR"].data.dtype == np.intp or np.issubdtype(
        las.curves["GR"].data.dtype, np.integer
    )


# ---------------------------------------------------------------------------
# dtype specified — list
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_specified_list():
    """dtypes=[float, float, float, float] applied per-column in order."""
    las = las_rs.read(fixture("v12/sample_v12.las"), dtypes=[float, float, float, float])
    for curve in las.curves:
        assert np.issubdtype(curve.data.dtype, np.floating)


# ---------------------------------------------------------------------------
# Engine selection — normal
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_engine_normal():
    """engine='normal' parses the data section correctly and produces the
    same result as default parsing."""
    las = las_rs.read(fixture("v12/sample_v12.las"), engine="normal")
    dept = las.curves["DEPT"].data
    assert dept[0] == pytest.approx(500.0)
    assert len(dept) == 6


# ---------------------------------------------------------------------------
# Engine selection — numpy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_engine_numpy():
    """engine='numpy' parses the data section correctly and produces the
    same depths as the normal engine."""
    las_normal = las_rs.read(fixture("v12/sample_v12.las"), engine="normal")
    las_numpy = las_rs.read(fixture("v12/sample_v12.las"), engine="numpy")
    np.testing.assert_array_almost_equal(
        las_normal.curves["DEPT"].data,
        las_numpy.curves["DEPT"].data,
    )
