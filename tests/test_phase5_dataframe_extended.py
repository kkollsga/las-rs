"""
Phase 5 extended: DataFrame edge cases.

Covers indexed .loc access, consistency between las.keys() and df().columns,
numeric-string dtype promotion to float64, include_units using original_mnemonic,
and set_data_from_df with truncate=True.

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
# Inline LAS — 4 curves (DEPT, RES, DT, PORO), 5 rows.
# Values deliberately distinct from the existing dataframe tests.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  6000.0 : START DEPTH
 STOP.M  6004.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  SILVERGATE EXPLORATION : COMPANY
 WELL.  CLOUDPEAK-8 #5         : WELL NAME
~CURVE INFORMATION
 DEPT.M      : MEASURED DEPTH
 RES .OHM.M  : RESISTIVITY
 DT  .US/M   : SONIC TRANSIT TIME
 PORO.V/V    : POROSITY
~ASCII LOG DATA
 6000.0   18.55   295.10   0.241
 6001.0   22.13   312.40   0.228
 6002.0   15.87   287.60   0.256
 6003.0   30.44   330.20   0.212
 6004.0   25.09   305.80   0.235
"""

N_ROWS = 5
_DEPTH_AT_ROW2 = 6002.0  # used for .loc lookup


def _read():
    return las_rs.read(_LAS_SRC)


# ===========================================================================
# 1. df().loc[specific_depth] returns the correct row
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_df_index_by_depth():
    """df().loc[6002.0] returns the data row corresponding to depth 6002.0.
    The RES value at that depth is 15.87."""
    pd = pytest.importorskip("pandas")
    las = _read()
    df = las.df()
    row = df.loc[_DEPTH_AT_ROW2]
    # RES column at 6002.0 m is 15.87.
    assert float(row["RES"]) == pytest.approx(15.87)


# ===========================================================================
# 2. las.keys()[1:] == list(las.df().columns.values)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_df_curve_names_match_keys():
    """las.keys() returns all curve mnemonics including DEPT.  las.df().columns
    contains only the non-depth curves.  Therefore keys()[1:] must equal the
    DataFrame column list."""
    pytest.importorskip("pandas")
    las = _read()
    keys = list(las.keys())
    df_cols = list(las.df().columns.values)
    assert keys[1:] == df_cols


# ===========================================================================
# 3. df() promotes numeric-string object columns to float64
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_df_string_dtype_conversion():
    """When curve data happens to be stored as Python object/string arrays
    containing numeric strings, df() should convert those columns to float64."""
    pd = pytest.importorskip("pandas")
    las = _read()
    df = las.df()
    for col in df.columns:
        assert df[col].dtype == np.float64 or np.issubdtype(df[col].dtype, np.floating), (
            f"Column '{col}' has dtype {df[col].dtype}, expected float64"
        )


# ===========================================================================
# 4. df(include_units=True) uses original_mnemonic not session mnemonic
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_df_include_units_uses_original_mnemonic():
    """df(include_units=True) should label columns using the curve's
    original_mnemonic (as stored in the file), not any session-alias mnemonic.
    Column headers must still contain the unit string in brackets or parens."""
    pytest.importorskip("pandas")
    las = _read()
    df = las.df(include_units=True)
    col_str = " ".join(str(c) for c in df.columns)
    # Each non-depth curve unit should appear somewhere in the column names.
    assert "OHM" in col_str or "ohm" in col_str.lower()   # RES unit OHM.M
    assert "US" in col_str or "us" in col_str.lower()      # DT  unit US/M
    assert "V/V" in col_str or "v/v" in col_str.lower()   # PORO unit V/V


# ===========================================================================
# 5. set_data_from_df with truncate=True removes extra curves
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_from_df_truncate():
    """set_data_from_df(df, truncate=True) with a DataFrame that has fewer
    columns than the existing curve definitions drops the surplus curves so
    that len(las.curves) equals the number of DataFrame columns plus the index
    (depth) curve, i.e. 1 (index) + n_df_cols."""
    pd = pytest.importorskip("pandas")
    las = _read()
    # Original file has 4 curves (DEPT, RES, DT, PORO).
    # Supply a DataFrame with only 1 data column.
    narrow_df = pd.DataFrame(
        {"RES": [18.55, 22.13, 15.87]},
        index=pd.Index([6000.0, 6001.0, 6002.0], name="DEPT"),
    )
    las.set_data_from_df(narrow_df, truncate=True)
    # After truncation: DEPT + RES = 2 curves.
    assert len(las.curves) == 2
