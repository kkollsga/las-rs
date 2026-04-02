"""
Phase 5c tests — pandas DataFrame integration.

Covers las.df(), DataFrame shape, index/column mapping, value fidelity,
optional unit embedding in column names, descending-index files,
las.set_data() from a raw numpy array, las.set_data_from_df(), and
set_data with explicit curve name overrides.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Inline LAS strings
# ---------------------------------------------------------------------------

# Ascending depth — 4 rows, 4 curves (DEPT, GR, NPHI, RHOB)
_LAS_ASC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   800.0 : START DEPTH
 STOP.M   803.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  MESA ENERGY INC : COMPANY
 WELL.  CONDOR-5 #2     : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 NPHI.V/V  : NEUTRON POROSITY
 RHOB.G/CC : BULK DENSITY
~ASCII LOG DATA
 800.0   38.74   0.3120   2.441
 801.0   55.60   0.2670   2.553
 802.0   71.22   0.2110   2.688
 803.0   48.95   0.2890   2.510
"""

# Descending depth — STRT > STOP, 3 rows
_LAS_DESC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   600.0 : START DEPTH
 STOP.M   598.0 : STOP DEPTH
 STEP.M    -1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  MESA ENERGY INC : COMPANY
 WELL.  CONDOR-5 #3     : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 SP  .MV   : SPONTANEOUS POTENTIAL
~ASCII LOG DATA
 600.0  -47.22
 599.0  -51.09
 598.0  -44.87
"""


def _read_asc():
    return las_rs.read(_LAS_ASC)


def _read_desc():
    return las_rs.read(_LAS_DESC)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_returns_dataframe():
    """las.df() returns a pandas DataFrame instance."""
    pd = pytest.importorskip("pandas")
    las = _read_asc()
    result = las.df()
    assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# Index is depth
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_index_is_depth():
    """The DataFrame index corresponds to the first curve (DEPT); the index
    values match the depth array exactly."""
    pd = pytest.importorskip("pandas")
    las = _read_asc()
    df = las.df()
    expected_depths = las.curves["DEPT"].data
    np.testing.assert_array_almost_equal(df.index.values, expected_depths)


# ---------------------------------------------------------------------------
# Columns are non-index curves
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_columns_are_curves():
    """The DataFrame columns are the non-depth curve mnemonics in declaration
    order: GR, NPHI, RHOB."""
    pytest.importorskip("pandas")
    las = _read_asc()
    df = las.df()
    assert list(df.columns) == ["GR", "NPHI", "RHOB"]


# ---------------------------------------------------------------------------
# Values match las.data
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_values_match_data():
    """DataFrame values are numerically identical to the corresponding columns
    in las.data (columns 1 onward, since column 0 is depth / index)."""
    pytest.importorskip("pandas")
    las = _read_asc()
    df = las.df()
    # las.data shape: (4, 4); columns 1..3 are GR, NPHI, RHOB
    expected = las.data[:, 1:]
    np.testing.assert_array_almost_equal(df.values, expected)


# ---------------------------------------------------------------------------
# include_units option
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_include_units():
    """df(include_units=True) decorates each column name with its unit in
    parentheses, e.g. 'GR (GAPI)'."""
    pytest.importorskip("pandas")
    las = _read_asc()
    df = las.df(include_units=True)
    col_strings = " ".join(df.columns)
    assert "GAPI" in col_strings
    assert "V/V" in col_strings or "v/v" in col_strings.lower()


# ---------------------------------------------------------------------------
# Descending index
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_df_reverse_index():
    """A file whose STRT > STOP (descending depth) produces a DataFrame whose
    index is monotonically decreasing."""
    pytest.importorskip("pandas")
    las = _read_desc()
    df = las.df()
    idx = df.index.values
    # Each successive depth value should be less than the previous one.
    assert all(idx[i] > idx[i + 1] for i in range(len(idx) - 1))


# ---------------------------------------------------------------------------
# set_data from numpy array
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_from_array():
    """las.set_data(array) replaces the curve data; the new DEPT values are
    accessible via las.curves['DEPT'].data."""
    las = _read_asc()
    new_data = np.array([
        [1000.0, 22.10, 0.310, 2.501],
        [1001.0, 35.40, 0.290, 2.543],
        [1002.0, 48.70, 0.270, 2.589],
    ])
    las.set_data(new_data)
    np.testing.assert_array_almost_equal(
        las.curves["DEPT"].data, [1000.0, 1001.0, 1002.0]
    )


# ---------------------------------------------------------------------------
# set_data_from_df
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_from_df():
    """las.set_data_from_df(df) populates las.data from a pandas DataFrame;
    the depth index is stored as the first curve."""
    pd = pytest.importorskip("pandas")
    las = _read_asc()
    new_df = pd.DataFrame(
        {"GR": [10.0, 20.0], "NPHI": [0.30, 0.28], "RHOB": [2.45, 2.50]},
        index=pd.Index([2000.0, 2001.0], name="DEPT"),
    )
    las.set_data_from_df(new_df)
    dept = las.curves["DEPT"].data
    assert dept[0] == pytest.approx(2000.0)
    assert dept[1] == pytest.approx(2001.0)


# ---------------------------------------------------------------------------
# set_data with explicit names
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_with_names():
    """las.set_data(array, names=['DEPTH','RES','SP']) renames the curves in
    las.curves to match the supplied list."""
    las = _read_asc()
    new_data = np.array([
        [400.0, 12.5, -30.1],
        [401.0, 15.3, -28.7],
    ])
    las.set_data(new_data, names=["DEPTH", "RES", "SP"])
    curve_names = [c.mnemonic for c in las.curves]
    assert "DEPTH" in curve_names
    assert "RES" in curve_names
    assert "SP" in curve_names
