"""
Phase 1 tests — CurveItem core data type.

CurveItem extends HeaderItem with a numpy data array that holds the actual
log samples.  It also exposes API_code as an alias for the .value field.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import json

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEPTH_SAMPLES = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
GR_SAMPLES    = np.array([25.3, 48.7, 102.1, 87.6, 33.9])


def make_depth_curve():
    """Return a CurveItem representing a depth track."""
    return las_rs.CurveItem(
        mnemonic="DEPT",
        unit="M",
        value="",
        descr="Measured depth",
        data=DEPTH_SAMPLES,
    )


def make_gr_curve():
    """Return a CurveItem representing a gamma-ray track."""
    return las_rs.CurveItem(
        mnemonic="GR",
        unit="GAPI",
        value="45 690 01 00 43",
        descr="Gamma ray",
        data=GR_SAMPLES,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_create_default():
    """A CurveItem created with no arguments has an empty numpy data array."""
    item = las_rs.CurveItem()
    assert hasattr(item, "data")
    assert len(item.data) == 0


@pytest.mark.xfail(reason="not yet implemented")
def test_create_with_data():
    """Data passed at construction is accessible via .data."""
    item = make_depth_curve()
    np.testing.assert_array_equal(item.data, DEPTH_SAMPLES)


# ---------------------------------------------------------------------------
# data attribute type
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_data_is_numpy():
    """The .data attribute is a numpy ndarray."""
    item = make_depth_curve()
    assert isinstance(item.data, np.ndarray)


# ---------------------------------------------------------------------------
# API_code alias
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_api_code_property():
    """API_code is an alias for .value and returns the same string."""
    item = make_gr_curve()
    assert item.API_code == item.value
    assert item.API_code == "45 690 01 00 43"


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_repr_includes_shape():
    """repr of a CurveItem includes the shape of the data array."""
    item = make_gr_curve()
    r = repr(item)
    # The shape tuple (5,) should appear somewhere in the string
    assert "5" in r
    assert "GR" in r


# ---------------------------------------------------------------------------
# json property
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_json_includes_data():
    """The json property includes the data samples as a list."""
    item = make_depth_curve()
    parsed = json.loads(item.json)
    assert "data" in parsed
    assert parsed["data"] == pytest.approx(DEPTH_SAMPLES.tolist())


@pytest.mark.xfail(reason="not yet implemented")
def test_json_setter_blocked():
    """Setting the json property raises an Exception."""
    item = make_depth_curve()
    with pytest.raises(Exception):
        item.json = '{"mnemonic": "FAKE"}'
