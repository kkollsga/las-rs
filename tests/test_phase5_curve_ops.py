"""
Phase 5d tests — Curve manipulation.

Covers appending, inserting, and deleting curves by mnemonic and index,
updating curve data and units, __setitem__ / __getitem__ / dict-style access,
and the CurveItem-level helpers (append_curve_item, replace_curve_item).

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
# Inline LAS used as the base for all manipulation tests.
# 3 curves (DEPT, GR, SP), 5 rows.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  2000.0 : START DEPTH
 STOP.M  2004.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  CANYON DRILLING INC : COMPANY
 WELL.  REDROCK-7 #4        : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 SP  .MV   : SPONTANEOUS POTENTIAL
~ASCII LOG DATA
 2000.0   51.14  -44.22
 2001.0   63.77  -50.88
 2002.0   78.32  -57.31
 2003.0   59.05  -48.66
 2004.0   44.90  -41.75
"""

N_ROWS = 5

NEW_DATA    = np.array([1.1, 2.2, 3.3, 4.4, 5.5])
UPDATED_GR  = np.array([10.0, 20.0, 30.0, 40.0, 50.0])


def _read():
    return las_rs.read(_LAS_SRC)


# ===========================================================================
# Append
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_append_curve():
    """append_curve(mnemonic, data) adds a new curve at the end; the resulting
    las.curves collection has one more item than before."""
    las = _read()
    before = len(las.curves)
    las.append_curve("CALI", NEW_DATA)
    assert len(las.curves) == before + 1
    assert las.curves[-1].mnemonic == "CALI"


@pytest.mark.xfail(reason="not yet implemented")
def test_append_curve_with_metadata():
    """append_curve accepts optional unit and descr keyword arguments that are
    stored on the new CurveItem."""
    las = _read()
    las.append_curve("CALI", NEW_DATA, unit="IN", descr="Caliper log")
    item = las.get_curve("CALI")
    assert item.unit == "IN"
    assert "Caliper" in item.descr or item.descr == "Caliper log"


# ===========================================================================
# Insert
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_insert_curve():
    """insert_curve(1, mnemonic, data) places the new curve at position 1,
    pushing existing curves at index 1+ one position to the right."""
    las = _read()
    las.insert_curve(1, "RHOB", NEW_DATA)
    assert las.curves[1].mnemonic == "RHOB"
    # Original second curve (GR) is now at index 2
    assert las.curves[2].mnemonic == "GR"


# ===========================================================================
# Delete
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_delete_curve_by_mnemonic():
    """delete_curve(mnemonic='GR') removes the GR curve; it no longer appears
    in las.curves and the total count decreases by one."""
    las = _read()
    before = len(las.curves)
    las.delete_curve(mnemonic="GR")
    assert len(las.curves) == before - 1
    mnemonics = [c.mnemonic for c in las.curves]
    assert "GR" not in mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_delete_curve_by_index():
    """delete_curve(ix=2) removes the curve at position 2 (SP in the inline
    fixture); the count decreases by one."""
    las = _read()
    before = len(las.curves)
    las.delete_curve(ix=2)
    assert len(las.curves) == before - 1


# ===========================================================================
# Update
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_update_curve_data():
    """update_curve(mnemonic='GR', data=new_array) replaces the data array
    for GR with the supplied values."""
    las = _read()
    las.update_curve(mnemonic="GR", data=UPDATED_GR)
    np.testing.assert_array_almost_equal(las.curves["GR"].data, UPDATED_GR)


@pytest.mark.xfail(reason="not yet implemented")
def test_update_curve_unit():
    """update_curve(mnemonic='GR', unit='API') changes the unit stored on the
    GR CurveItem without altering the data array."""
    las = _read()
    original_data = las.curves["GR"].data.copy()
    las.update_curve(mnemonic="GR", unit="API")
    assert las.get_curve("GR").unit == "API"
    np.testing.assert_array_almost_equal(las.curves["GR"].data, original_data)


# ===========================================================================
# __setitem__
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_new_curve():
    """las['EXTRA'] = numpy_array appends a new curve named EXTRA to the end
    of las.curves."""
    las = _read()
    before = len(las.curves)
    las["EXTRA"] = NEW_DATA
    assert len(las.curves) == before + 1
    mnemonics = [c.mnemonic for c in las.curves]
    assert "EXTRA" in mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_existing_updates():
    """las['GR'] = new_array updates the data for the existing GR curve rather
    than adding a duplicate."""
    las = _read()
    before = len(las.curves)
    las["GR"] = UPDATED_GR
    # Count must not increase
    assert len(las.curves) == before
    np.testing.assert_array_almost_equal(las["GR"], UPDATED_GR)


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_curve_item():
    """las['EXTRA'] = CurveItem(...) appends the CurveItem when its mnemonic
    matches the key."""
    las = _read()
    before = len(las.curves)
    item = las_rs.CurveItem(mnemonic="EXTRA", unit="OHM", data=NEW_DATA)
    las["EXTRA"] = item
    assert len(las.curves) == before + 1
    assert las.get_curve("EXTRA").unit == "OHM"


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_mismatch_raises():
    """las['X'] = CurveItem(mnemonic='Y') raises KeyError because the key
    and the CurveItem mnemonic disagree."""
    las = _read()
    item = las_rs.CurveItem(mnemonic="Y", data=NEW_DATA)
    with pytest.raises(KeyError):
        las["X"] = item


# ===========================================================================
# __getitem__
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_mnemonic():
    """las['GR'] returns the numpy data array for the GR curve."""
    las = _read()
    result = las["GR"]
    assert isinstance(result, np.ndarray)
    assert len(result) == N_ROWS


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_int():
    """las[1] returns the data array of the second curve (GR at index 1)."""
    las = _read()
    result = las[1]
    assert isinstance(result, np.ndarray)
    assert len(result) == N_ROWS
    # Should equal the GR data
    np.testing.assert_array_almost_equal(result, las["GR"])


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_negative_int():
    """las[-1] returns the data array of the last curve (SP)."""
    las = _read()
    result = las[-1]
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_almost_equal(result, las["SP"])


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_missing_raises():
    """las['BOGUS'] raises KeyError for a mnemonic that does not exist."""
    las = _read()
    with pytest.raises(KeyError):
        _ = las["BOGUS"]


# ===========================================================================
# Mapping-style helpers
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_keys_values_items():
    """las.keys() returns curve mnemonics, las.values() returns data arrays,
    and las.items() returns (mnemonic, data) pairs; all three are consistent."""
    las = _read()
    keys   = list(las.keys())
    values = list(las.values())
    items  = list(las.items())

    assert keys == ["DEPT", "GR", "SP"]
    assert len(values) == 3
    assert len(items) == 3

    for (k, v), key, val in zip(items, keys, values):
        assert k == key
        np.testing.assert_array_almost_equal(v, val)


# ===========================================================================
# get_curve
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_get_curve():
    """las.get_curve('GR') returns a CurveItem object (not a raw array) with
    the correct mnemonic and unit attributes."""
    las = _read()
    item = las.get_curve("GR")
    assert isinstance(item, las_rs.CurveItem)
    assert item.mnemonic == "GR"
    assert item.unit == "GAPI"


# ===========================================================================
# append_curve_item / replace_curve_item
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_append_curve_item():
    """append_curve_item(CurveItem) appends the item to the curves list; the
    mnemonic is accessible via las.get_curve()."""
    las = _read()
    before = len(las.curves)
    new_item = las_rs.CurveItem(mnemonic="CALI", unit="IN", data=NEW_DATA)
    las.append_curve_item(new_item)
    assert len(las.curves) == before + 1
    assert las.get_curve("CALI").mnemonic == "CALI"


@pytest.mark.xfail(reason="not yet implemented")
def test_replace_curve_item():
    """replace_curve_item(ix, CurveItem) replaces the curve at position *ix*
    with the supplied CurveItem; the old mnemonic at that position is gone."""
    las = _read()
    replacement = las_rs.CurveItem(mnemonic="DT", unit="US/M", data=NEW_DATA)
    las.replace_curve_item(1, replacement)   # replace GR at index 1
    assert las.curves[1].mnemonic == "DT"
    mnemonics = [c.mnemonic for c in las.curves]
    assert "GR" not in mnemonics
