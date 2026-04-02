"""
Phase 5 extended: Curve manipulation edge cases.

Covers update_curve by integer index, descr/value changes, CurveItem __setitem__
replacement, duplicate-mnemonic handling, missing-curve KeyError, set_data with
truncate, set_data auto-creating unnamed curves, and set_data_from_df index/column
semantics.

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
# Inline LAS — 3 curves (DEPT, GR, SP), 5 rows.
# Deliberately different values from the existing curve-ops tests.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  4100.0 : START DEPTH
 STOP.M  4104.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  IRONSTONE ENERGY CORP : COMPANY
 WELL.  BLUERIDGE-11 #2       : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 SP  .MV   : SPONTANEOUS POTENTIAL
~ASCII LOG DATA
 4100.0   82.41  -62.10
 4101.0   91.07  -70.55
 4102.0   73.88  -58.33
 4103.0   65.50  -52.77
 4104.0   78.23  -61.89
"""

N_ROWS = 5

_NEW_DATA = np.array([5.5, 10.10, 15.15, 20.20, 25.25])


def _read():
    return las_rs.read(_LAS_SRC)


# ===========================================================================
# 1. update_curve by integer index
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_update_curve_by_ix():
    """update_curve(ix=2, data=new_array) updates the curve at position 2 (SP)
    by integer index, leaving the mnemonic and unit unchanged."""
    las = _read()
    replacement = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    las.update_curve(ix=2, data=replacement)
    np.testing.assert_array_almost_equal(las.curves[2].data, replacement)
    # mnemonic must still be SP
    assert las.curves[2].mnemonic == "SP"


# ===========================================================================
# 2. update_curve changes descr
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_update_curve_descr():
    """update_curve(mnemonic='GR', descr='New description') changes the descr
    attribute of the GR CurveItem without touching the data array."""
    las = _read()
    original_data = las.curves["GR"].data.copy()
    las.update_curve(mnemonic="GR", descr="New description")
    assert las.get_curve("GR").descr == "New description"
    np.testing.assert_array_almost_equal(las.curves["GR"].data, original_data)


# ===========================================================================
# 3. update_curve changes value
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_update_curve_value():
    """update_curve(mnemonic='GR', value='API_CODE') sets the value field on
    the GR CurveItem without touching the data array."""
    las = _read()
    original_data = las.curves["GR"].data.copy()
    las.update_curve(mnemonic="GR", value="API_CODE")
    assert las.get_curve("GR").value == "API_CODE"
    np.testing.assert_array_almost_equal(las.curves["GR"].data, original_data)


# ===========================================================================
# 4. __setitem__ with CurveItem replaces existing curve
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_curveitem_replaces_existing():
    """las['GR'] = CurveItem(mnemonic='GR', ...) replaces the existing GR
    curve in-place; the total curve count must not increase."""
    las = _read()
    before_count = len(las.curves)
    replacement_data = np.array([9.9, 8.8, 7.7, 6.6, 5.5])
    new_item = las_rs.CurveItem(
        mnemonic="GR", unit="API", data=replacement_data, descr="Replaced GR"
    )
    las["GR"] = new_item
    # Count unchanged — this is a replacement, not an addition.
    assert len(las.curves) == before_count
    # New unit and data should be stored.
    retrieved = las.get_curve("GR")
    assert retrieved.unit == "API"
    np.testing.assert_array_almost_equal(retrieved.data, replacement_data)


# ===========================================================================
# 5. Duplicate mnemonic via append_curve at LASFile level
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_duplicate_append_at_lasfile_level():
    """Appending a curve whose mnemonic already exists ('GR') should store both
    curves, disambiguated as 'GR:1' and 'GR:2' (or similar), so that neither
    curve is silently discarded."""
    las = _read()
    extra_data = np.array([11.1, 22.2, 33.3, 44.4, 55.5])
    las.append_curve("GR", extra_data, unit="GAPI", descr="Duplicate GR")
    mnemonics = [c.mnemonic for c in las.curves]
    # Both entries for GR must be present, possibly with disambiguation suffixes.
    gr_entries = [m for m in mnemonics if "GR" in m]
    assert len(gr_entries) >= 2


# ===========================================================================
# 6. Missing curve __getitem__ raises KeyError with informative message
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_missing_curve_getitem_keyerror():
    """las['NONEXIST'] raises KeyError when the mnemonic is absent; the
    exception message should mention at least one available curve name so the
    user knows what curves exist."""
    las = _read()
    with pytest.raises(KeyError) as exc_info:
        _ = las["NONEXIST"]
    # The error message should be informative — at minimum it should not be
    # blank.  Ideally it lists available curves such as DEPT, GR, SP.
    msg = str(exc_info.value)
    assert msg  # non-empty


# ===========================================================================
# 7. set_data with truncate=True removes extra curve definitions
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_truncate():
    """las.set_data(array, truncate=True) with fewer columns than existing
    curves removes the surplus curve definitions so that len(las.curves) equals
    the number of columns in the supplied array."""
    las = _read()
    # Supply only 2 columns (DEPT + GR) instead of 3.
    two_col = np.array([
        [4100.0, 82.41],
        [4101.0, 91.07],
        [4102.0, 73.88],
        [4103.0, 65.50],
        [4104.0, 78.23],
    ])
    las.set_data(two_col, truncate=True)
    assert len(las.curves) == 2


# ===========================================================================
# 8. set_data with more columns auto-creates unnamed curves
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_extends_curves():
    """las.set_data(wider_array) where the array has more columns than defined
    curves auto-creates placeholder CurveItem entries for the extra columns so
    that len(las.curves) equals the column count."""
    las = _read()
    # 5 columns but only 3 curves defined.
    five_col = np.column_stack([
        np.array([4100.0, 4101.0, 4102.0, 4103.0, 4104.0]),
        _NEW_DATA,
        _NEW_DATA * 2,
        _NEW_DATA * 3,
        _NEW_DATA * 4,
    ])
    las.set_data(five_col)
    assert len(las.curves) >= 5


# ===========================================================================
# 9. set_data_from_df uses DataFrame index as first curve
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_from_df_index_becomes_first_curve():
    """las.set_data_from_df(df) interprets the DataFrame index as the depth
    (first) curve.  After the call, the first curve's data matches the index
    values that were in the DataFrame."""
    pd = pytest.importorskip("pandas")
    las = _read()
    new_depths = [7000.0, 7001.0, 7002.0]
    df = pd.DataFrame(
        {"GR": [44.1, 55.2, 66.3], "SP": [-30.1, -35.2, -40.3]},
        index=pd.Index(new_depths, name="DEPT"),
    )
    las.set_data_from_df(df)
    first_curve_data = las.curves[0].data
    np.testing.assert_array_almost_equal(first_curve_data, new_depths)


# ===========================================================================
# 10. set_data_from_df uses DataFrame column names as curve mnemonics
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_set_data_from_df_column_names():
    """set_data_from_df(df) uses the column names of the DataFrame as curve
    mnemonics for all non-index curves."""
    pd = pytest.importorskip("pandas")
    las = _read()
    df = pd.DataFrame(
        {"RHOB": [2.41, 2.53, 2.68], "NPHI": [0.31, 0.27, 0.22]},
        index=pd.Index([4100.0, 4101.0, 4102.0], name="DEPT"),
    )
    las.set_data_from_df(df)
    mnemonics = [c.mnemonic for c in las.curves]
    assert "RHOB" in mnemonics
    assert "NPHI" in mnemonics
