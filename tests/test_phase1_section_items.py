"""
Phase 1 tests — SectionItems core data type.

SectionItems is a list subclass that holds HeaderItem or CurveItem objects
and provides dict-like access by mnemonic.  It also supports attribute-style
access, duplicate-mnemonic disambiguation, case-insensitive lookup, and
several dict-view helpers.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import json

import pytest

import las_rs


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def item(mnemonic, unit="", value="", descr=""):
    return las_rs.HeaderItem(mnemonic=mnemonic, unit=unit, value=value, descr=descr)


def well_section():
    """Return a small SectionItems populated with well-header entries."""
    sec = las_rs.SectionItems()
    sec.append(item("WELL", value="WILDCAT-12"))
    sec.append(item("FLD",  value="BLOCK_22"))
    sec.append(item("LOC",  value="55.123 N, 4.567 W"))
    sec.append(item("PROV", value="NORTH_SEA"))
    return sec


def curve_section():
    """Return a SectionItems holding channel definitions."""
    sec = las_rs.SectionItems()
    sec.append(item("DEPT", unit="M",    descr="Measured depth"))
    sec.append(item("GR",   unit="GAPI", descr="Gamma ray"))
    sec.append(item("RHOB", unit="G/CC", descr="Bulk density"))
    return sec


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_create_empty():
    """An empty SectionItems has length zero."""
    sec = las_rs.SectionItems()
    assert len(sec) == 0


@pytest.mark.xfail(reason="not yet implemented")
def test_append_and_length():
    """Appending items correctly increments the length."""
    sec = las_rs.SectionItems()
    sec.append(item("STRT", unit="M", value=500.0, descr="Start depth"))
    sec.append(item("STOP", unit="M", value=1500.0, descr="Stop depth"))
    assert len(sec) == 2


# ---------------------------------------------------------------------------
# __getitem__
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_mnemonic():
    """Accessing a SectionItems by mnemonic string returns the matching item."""
    sec = well_section()
    retrieved = sec["WELL"]
    assert retrieved.mnemonic == "WELL"
    assert retrieved.value == "WILDCAT-12"


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_index():
    """Accessing a SectionItems by integer index returns the item at that position."""
    sec = well_section()
    first = sec[0]
    assert first.mnemonic == "WELL"


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_by_slice():
    """Slicing a SectionItems returns a SectionItems with the matching subset."""
    sec = well_section()
    subset = sec[1:3]
    assert isinstance(subset, las_rs.SectionItems)
    assert len(subset) == 2
    assert subset[0].mnemonic == "FLD"
    assert subset[1].mnemonic == "LOC"


@pytest.mark.xfail(reason="not yet implemented")
def test_getitem_missing_raises():
    """Accessing a non-existent mnemonic raises KeyError."""
    sec = well_section()
    with pytest.raises(KeyError):
        _ = sec["NONEXISTENT_KEY"]


# ---------------------------------------------------------------------------
# __contains__
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_contains_by_mnemonic():
    """'GR' in section returns True when GR is present."""
    sec = curve_section()
    assert "GR" in sec


@pytest.mark.xfail(reason="not yet implemented")
def test_contains_by_item():
    """A HeaderItem object itself is found via the 'in' operator."""
    sec = curve_section()
    gr_item = sec["GR"]
    assert gr_item in sec


# ---------------------------------------------------------------------------
# __setitem__
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_replaces_value():
    """Setting a mnemonic key to a plain string updates the item's .value."""
    sec = well_section()
    sec["WELL"] = "WILDCAT-99"
    assert sec["WELL"].value == "WILDCAT-99"
    assert sec["WELL"].mnemonic == "WELL"


@pytest.mark.xfail(reason="not yet implemented")
def test_setitem_replaces_item():
    """Setting a mnemonic key to a HeaderItem replaces the whole item."""
    sec = well_section()
    new_item = las_rs.HeaderItem(
        mnemonic="WELL",
        unit="",
        value="REPLACEMENT-3",
        descr="Updated well name",
    )
    sec["WELL"] = new_item
    assert sec["WELL"].value == "REPLACEMENT-3"
    assert sec["WELL"].descr == "Updated well name"


# ---------------------------------------------------------------------------
# __delitem__
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_delitem_by_mnemonic():
    """Deleting by mnemonic string removes that entry from the section."""
    sec = well_section()
    original_len = len(sec)
    del sec["PROV"]
    assert len(sec) == original_len - 1
    assert "PROV" not in sec


@pytest.mark.xfail(reason="not yet implemented")
def test_delitem_by_index():
    """Deleting by integer index removes the item at that position."""
    sec = well_section()
    original_len = len(sec)
    del sec[0]
    assert len(sec) == original_len - 1
    assert "WELL" not in sec


# ---------------------------------------------------------------------------
# keys / values / items
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_keys_returns_mnemonics():
    """keys() returns a list of mnemonic strings in insertion order."""
    sec = curve_section()
    assert list(sec.keys()) == ["DEPT", "GR", "RHOB"]


@pytest.mark.xfail(reason="not yet implemented")
def test_values_returns_items():
    """values() returns the HeaderItem objects in insertion order."""
    sec = curve_section()
    vals = list(sec.values())
    assert all(isinstance(v, las_rs.HeaderItem) for v in vals)
    assert vals[0].mnemonic == "DEPT"


@pytest.mark.xfail(reason="not yet implemented")
def test_items_returns_pairs():
    """items() returns (mnemonic, HeaderItem) pairs in insertion order."""
    sec = curve_section()
    pairs = list(sec.items())
    assert pairs[0] == ("DEPT", sec["DEPT"])
    assert pairs[1] == ("GR",   sec["GR"])
    assert pairs[2] == ("RHOB", sec["RHOB"])


# ---------------------------------------------------------------------------
# Duplicate mnemonics
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_duplicate_mnemonic_suffixes():
    """Two items with the same mnemonic receive ':1' and ':2' session suffixes."""
    sec = las_rs.SectionItems()
    sec.append(item("RETN", value="first"))
    sec.append(item("RETN", value="second"))
    mnemonics = list(sec.keys())
    assert "RETN:1" in mnemonics
    assert "RETN:2" in mnemonics


# ---------------------------------------------------------------------------
# Attribute-style access
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_attr_access_read():
    """section.GR returns the HeaderItem with mnemonic 'GR'."""
    sec = curve_section()
    assert sec.GR.mnemonic == "GR"
    assert sec.GR.unit == "GAPI"


@pytest.mark.xfail(reason="not yet implemented")
def test_attr_access_write():
    """Assigning section.GR = value sets GR item's .value."""
    sec = curve_section()
    sec.GR = "150.0"
    assert sec["GR"].value == "150.0"


# ---------------------------------------------------------------------------
# Case-sensitivity behaviour
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_insensitive():
    """With mnemonic_transforms=True, 'gr' matches the 'GR' item."""
    sec = las_rs.SectionItems(mnemonic_transforms=True)
    sec.append(item("GR", unit="GAPI", descr="Gamma ray"))
    assert sec["gr"].mnemonic == "GR"


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_sensitive():
    """With mnemonic_transforms=False, 'gr' does NOT match 'GR'."""
    sec = las_rs.SectionItems(mnemonic_transforms=False)
    sec.append(item("GR", unit="GAPI", descr="Gamma ray"))
    with pytest.raises(KeyError):
        _ = sec["gr"]


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_get_existing():
    """get('GR') returns the existing GR HeaderItem."""
    sec = curve_section()
    result = sec.get("GR")
    assert result.mnemonic == "GR"


@pytest.mark.xfail(reason="not yet implemented")
def test_get_missing_string_default():
    """get('MISSING', 'fallback_val') returns a new HeaderItem whose value is 'fallback_val'."""
    sec = well_section()
    result = sec.get("MISSING", "fallback_val")
    assert isinstance(result, las_rs.HeaderItem)
    assert result.value == "fallback_val"


@pytest.mark.xfail(reason="not yet implemented")
def test_get_missing_add():
    """get('MISSING', add=True) appends a new blank item and returns it."""
    sec = well_section()
    original_len = len(sec)
    result = sec.get("NEWFIELD", add=True)
    assert isinstance(result, las_rs.HeaderItem)
    assert len(sec) == original_len + 1
    assert "NEWFIELD" in sec


# ---------------------------------------------------------------------------
# dictview
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_dictview():
    """dictview() returns a plain dict mapping mnemonic -> value."""
    sec = well_section()
    view = sec.dictview()
    assert isinstance(view, dict)
    assert view["WELL"] == "WILDCAT-12"
    assert view["FLD"] == "BLOCK_22"


# ---------------------------------------------------------------------------
# str / table format
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_str_table_format():
    """str(section) produces an aligned table with mnemonic and value columns."""
    sec = curve_section()
    table = str(sec)
    assert "DEPT" in table
    assert "GR" in table
    assert "RHOB" in table
    # Each row should be on its own line
    lines = [l for l in table.splitlines() if l.strip()]
    assert len(lines) >= 3


# ---------------------------------------------------------------------------
# json property
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_json_property():
    """json property returns a valid JSON array of item objects."""
    sec = curve_section()
    raw = sec.json
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    assert len(parsed) == 3
    mnemonics = [entry["mnemonic"] for entry in parsed]
    assert "DEPT" in mnemonics
    assert "GR" in mnemonics
    assert "RHOB" in mnemonics
