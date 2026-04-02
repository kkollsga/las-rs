"""
Phase 1 tests — HeaderItem core data type.

HeaderItem is an OrderedDict subclass that represents a single entry in a
LAS file header section (e.g. one line from the ~WELL or ~CURVE block).
Each instance carries: mnemonic, unit, value, descr, and data fields.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import json
import pickle

import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_caliper():
    """Return a typical HeaderItem representing a caliper channel."""
    return las_rs.HeaderItem(
        mnemonic="CALI",
        unit="IN",
        value=8.5,
        descr="Caliper log",
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_create_default():
    """Creating a HeaderItem with no arguments yields empty-string defaults."""
    item = las_rs.HeaderItem()
    assert item.mnemonic == ""
    assert item.unit == ""
    assert item.value == ""
    assert item.descr == ""
    assert item.data == ""


@pytest.mark.xfail(reason="not yet implemented")
def test_create_with_values():
    """All constructor keyword arguments are stored correctly."""
    item = las_rs.HeaderItem(
        mnemonic="CALI",
        unit="IN",
        value=8.5,
        descr="Caliper log",
    )
    assert item.mnemonic == "CALI"
    assert item.unit == "IN"
    assert item.value == 8.5
    assert item.descr == "Caliper log"


# ---------------------------------------------------------------------------
# original_mnemonic
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_original_mnemonic_stored():
    """original_mnemonic preserves the raw mnemonic passed at construction."""
    item = las_rs.HeaderItem(mnemonic="RHOB", unit="G/CC", value=2.65, descr="Bulk density")
    assert item.original_mnemonic == "RHOB"


# ---------------------------------------------------------------------------
# useful_mnemonic
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_useful_mnemonic_nonempty():
    """useful_mnemonic returns the mnemonic when it is not blank."""
    item = las_rs.HeaderItem(mnemonic="GR", unit="GAPI", value=45.0, descr="Gamma ray")
    assert item.useful_mnemonic == "GR"


@pytest.mark.xfail(reason="not yet implemented")
def test_useful_mnemonic_blank():
    """useful_mnemonic returns 'UNKNOWN' when the mnemonic is an empty string."""
    item = las_rs.HeaderItem(mnemonic="", unit="", value="", descr="")
    assert item.useful_mnemonic == "UNKNOWN"


@pytest.mark.xfail(reason="not yet implemented")
def test_useful_mnemonic_readonly():
    """Assigning to useful_mnemonic raises ValueError."""
    item = las_rs.HeaderItem(mnemonic="DT", unit="US/F", value=72.3, descr="Sonic")
    with pytest.raises(ValueError):
        item.useful_mnemonic = "SOMETHING"


# ---------------------------------------------------------------------------
# mnemonic setter
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_set_mnemonic_updates_original():
    """Assigning to .mnemonic also updates original_mnemonic."""
    item = las_rs.HeaderItem(mnemonic="NPHI", unit="V/V", value=0.22, descr="Neutron porosity")
    item.mnemonic = "PHIND"
    assert item.original_mnemonic == "PHIND"
    assert item.mnemonic == "PHIND"


# ---------------------------------------------------------------------------
# Dict-style access
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_dict_access_mnemonic():
    """item['mnemonic'] returns the mnemonic string."""
    item = make_caliper()
    assert item["mnemonic"] == "CALI"


@pytest.mark.xfail(reason="not yet implemented")
def test_dict_access_unit():
    """item['unit'] returns the unit string."""
    item = make_caliper()
    assert item["unit"] == "IN"


@pytest.mark.xfail(reason="not yet implemented")
def test_dict_access_invalid_key():
    """Accessing an unrecognised key raises KeyError."""
    item = make_caliper()
    with pytest.raises(KeyError):
        _ = item["bogus"]


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_repr_format():
    """repr contains the class name and all four primary fields."""
    item = las_rs.HeaderItem(
        mnemonic="SP",
        unit="MV",
        value=-32.1,
        descr="Spontaneous potential",
    )
    r = repr(item)
    assert "HeaderItem" in r
    assert "SP" in r
    assert "MV" in r
    assert "-32.1" in r or "-32" in r
    assert "Spontaneous potential" in r


# ---------------------------------------------------------------------------
# json property
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_json_property():
    """json property returns a valid JSON string containing the item's fields."""
    item = las_rs.HeaderItem(
        mnemonic="PEFZ",
        unit="B/E",
        value=3.14,
        descr="Photoelectric factor",
    )
    raw = item.json
    parsed = json.loads(raw)
    assert parsed["mnemonic"] == "PEFZ"
    assert parsed["unit"] == "B/E"
    assert parsed["descr"] == "Photoelectric factor"


@pytest.mark.xfail(reason="not yet implemented")
def test_json_setter_blocked():
    """Setting the json property raises an Exception."""
    item = make_caliper()
    with pytest.raises(Exception):
        item.json = '{"mnemonic": "FAKE"}'


# ---------------------------------------------------------------------------
# Pickling
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_pickle_roundtrip():
    """Pickling and unpickling a HeaderItem preserves all fields."""
    original = las_rs.HeaderItem(
        mnemonic="ILD",
        unit="OHMM",
        value=12.7,
        descr="Deep resistivity",
    )
    restored = pickle.loads(pickle.dumps(original))
    assert restored.mnemonic == "ILD"
    assert restored.unit == "OHMM"
    assert restored.value == 12.7
    assert restored.descr == "Deep resistivity"
    assert restored.original_mnemonic == "ILD"
