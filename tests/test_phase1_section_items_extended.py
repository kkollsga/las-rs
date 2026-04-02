"""Phase 1 extended: SectionItems edge cases for public API coverage."""

import math

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hitem(mnemonic, unit="", value="", descr=""):
    return las_rs.HeaderItem(mnemonic=mnemonic, unit=unit, value=value, descr=descr)


def citem(mnemonic, unit="", value="", descr="", data=None):
    if data is None:
        data = np.array([])
    return las_rs.CurveItem(mnemonic=mnemonic, unit=unit, value=value, descr=descr, data=data)


def header_section():
    sec = las_rs.SectionItems()
    sec.append(hitem("WELL", value="RIDGE-5"))
    sec.append(hitem("FLD",  value="NORTHBLOCK"))
    sec.append(hitem("LOC",  value="60.00 N, 2.50 E"))
    return sec


def curve_section_with_data():
    """SectionItems with CurveItems that have data arrays of length 4."""
    sec = las_rs.SectionItems()
    sec.append(citem("DEPT", unit="M",    descr="Depth",     data=np.array([1000.0, 1001.0, 1002.0, 1003.0])))
    sec.append(citem("GR",   unit="GAPI", descr="Gamma ray", data=np.array([55.3, 62.1, 48.7, 71.0])))
    sec.append(citem("RHOB", unit="G/CC", descr="Density",   data=np.array([2.50, 2.48, 2.53, 2.45])))
    return sec


# ---------------------------------------------------------------------------
# 1. test_dict_style_setitem_mnemonic_blocked
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_dict_style_setitem_mnemonic_blocked():
    """item['mnemonic'] = 'ZZZ' does NOT change the mnemonic.

    The dict-key 'mnemonic' is read-only for SectionItems; only the
    .mnemonic attribute setter is the authoritative route.
    """
    sec = header_section()
    original_mnemonic = sec["WELL"].mnemonic
    # This should either be a no-op or raise; it must not silently rename the
    # underlying mnemonic that SectionItems uses for keying.
    try:
        sec["WELL"]["mnemonic"] = "ZZZ"
    except (TypeError, KeyError, AttributeError):
        pass
    # The item is still accessible under "WELL", not "ZZZ"
    assert "WELL" in sec
    assert sec["WELL"].mnemonic == original_mnemonic


# ---------------------------------------------------------------------------
# 2. test_get_missing_curveitem_default
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_get_missing_curveitem_default():
    """get('MISSING') on a CurveItem section returns a CurveItem with NaN data
    matching the length of existing curves."""
    sec = curve_section_with_data()
    result = sec.get("MISSING")
    assert isinstance(result, las_rs.CurveItem)
    # Length must match existing curve length (4)
    assert len(result.data) == 4
    # All values should be NaN
    assert all(math.isnan(v) for v in result.data)


# ---------------------------------------------------------------------------
# 3. test_get_missing_headeritem_default_object
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_get_missing_headeritem_default_object():
    """get('MISSING', default=HeaderItem(...)) returns a new item whose
    mnemonic is 'MISSING' but whose unit/value/descr come from the default."""
    sec = header_section()
    default = las_rs.HeaderItem(mnemonic="X", unit="DEGC", value="99", descr="template")
    result = sec.get("MISSING", default=default)
    assert isinstance(result, las_rs.HeaderItem)
    assert result.mnemonic == "MISSING"
    assert result.unit == "DEGC"
    assert result.value == "99"
    assert result.descr == "template"


# ---------------------------------------------------------------------------
# 4. test_get_missing_int_default
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_get_missing_int_default():
    """get('MISSING', 42) returns a HeaderItem with value coerced to '42'."""
    sec = header_section()
    result = sec.get("MISSING", 42)
    assert isinstance(result, las_rs.HeaderItem)
    assert str(result.value) == "42"


# ---------------------------------------------------------------------------
# 5. test_assign_duplicate_suffixes_all
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_assign_duplicate_suffixes_all():
    """assign_duplicate_suffixes(None) re-checks ALL mnemonics, not just one."""
    sec = las_rs.SectionItems()
    sec.append(hitem("GR", value="first"))
    sec.append(hitem("GR", value="second"))
    sec.append(hitem("SP", value="first_sp"))
    sec.append(hitem("SP", value="second_sp"))
    # Force a full re-check
    sec.assign_duplicate_suffixes(None)
    keys = list(sec.keys())
    # Both pairs must be disambiguated
    assert len(set(keys)) == len(keys), "All mnemonics must be unique after re-check"
    gr_keys = [k for k in keys if "GR" in k]
    sp_keys = [k for k in keys if "SP" in k]
    assert len(gr_keys) == 2
    assert len(sp_keys) == 2


# ---------------------------------------------------------------------------
# 6. test_set_item_appends_if_missing
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_set_item_appends_if_missing():
    """set_item('NEW', HeaderItem(...)) appends when 'NEW' doesn't exist."""
    sec = header_section()
    original_len = len(sec)
    new = hitem("NEW", value="brand_new")
    sec.set_item("NEW", new)
    assert len(sec) == original_len + 1
    assert "NEW" in sec
    assert sec["NEW"].value == "brand_new"


# ---------------------------------------------------------------------------
# 7. test_set_item_value_updates
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_set_item_value_updates():
    """set_item_value('GR', 99.0) changes the .value of the existing GR item."""
    sec = curve_section_with_data()
    sec.set_item_value("GR", 99.0)
    assert sec["GR"].value == 99.0 or str(sec["GR"].value) == "99.0"


# ---------------------------------------------------------------------------
# 8. test_mnemonic_rename_to_empty
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_multiple_duplicate_suffixes():
    """Three items named 'GR' become GR:1, GR:2, GR:3."""
    sec = las_rs.SectionItems()
    sec.append(hitem("GR", value="alpha"))
    sec.append(hitem("GR", value="beta"))
    sec.append(hitem("GR", value="gamma"))
    keys = list(sec.keys())
    assert "GR:1" in keys
    assert "GR:2" in keys
    assert "GR:3" in keys


# ---------------------------------------------------------------------------
# 10. test_insert_updates_duplicates
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_insert_updates_duplicates():
    """Inserting a duplicate mnemonic triggers re-suffixing of all copies."""
    sec = las_rs.SectionItems()
    sec.append(hitem("RHOB", value="first"))
    sec.append(hitem("NPHI", value="solo"))
    # Now insert a second RHOB — should trigger duplicate resolution
    sec.append(hitem("RHOB", value="second"))
    keys = list(sec.keys())
    rhob_keys = [k for k in keys if "RHOB" in k]
    # Both RHOB entries must be present with unique keys
    assert len(rhob_keys) == 2
    assert len(set(rhob_keys)) == 2
