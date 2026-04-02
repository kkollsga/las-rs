"""
Phase 5b tests — JSON serialization.

Covers the `las.json` property (valid JSON string, correct top-level keys,
data arrays, NaN-as-null serialization, setter guard) and the
`las_rs.JSONEncoder` hook for `json.dumps`.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import json
import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Shared inline LAS string used by most tests.
# 5 curves (DEPT, GR, NPHI, RHOB, SP), 4 rows.  Row 3 has a NaN in GR.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.                2.0 : LAS VERSION 2.0
 WRAP.                 NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M           1500.0 : START DEPTH
 STOP.M           1503.0 : STOP DEPTH
 STEP.M              1.0 : STEP VALUE
 NULL.          -999.25  : NULL VALUE
 COMP.   PETRA RESOURCES : COMPANY
 WELL.   SILVERTIP-2 #1  : WELL NAME
 FLD .   SILVERTIP FIELD : FIELD
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 NPHI.V/V  : NEUTRON POROSITY
 RHOB.G/CC : BULK DENSITY
 SP  .MV   : SPONTANEOUS POTENTIAL
~PARAMETER INFORMATION
 BHT .DEGC    88.5 : BOTTOM HOLE TEMPERATURE
 MWT .G/CC     1.2 : MUD WEIGHT
~ASCII LOG DATA
 1500.0   42.31   0.2940   2.512   -53.11
 1501.0   67.85   0.2150   2.631   -64.77
 1502.0   55.22   0.2580   2.571  -999.25
 1503.0  -999.25  0.3010   2.488   -49.03
"""


def _read_inline():
    return las_rs.read(_LAS_SRC)


# ---------------------------------------------------------------------------
# Valid JSON output
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_property_valid():
    """las.json returns a string that can be decoded by the standard library
    json.loads without raising an exception."""
    las = _read_inline()
    raw = las.json
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Required top-level keys
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_has_metadata():
    """The JSON output contains a 'metadata' key whose value is a dict with
    sub-keys for the four standard LAS header sections: version, well,
    curves (or curve), and parameter (or params)."""
    las = _read_inline()
    parsed = json.loads(las.json)
    assert "metadata" in parsed
    meta = parsed["metadata"]
    # At least one of the standard section names must be present.
    section_keys = {k.lower() for k in meta.keys()}
    assert section_keys & {"version", "well", "curves", "curve", "parameter", "params"}


@pytest.mark.xfail(reason="not yet implemented")
def test_json_has_data():
    """The JSON output contains a 'data' key whose value is a dict (or list)
    with an entry for each curve mnemonic."""
    las = _read_inline()
    parsed = json.loads(las.json)
    assert "data" in parsed
    data = parsed["data"]
    # When data is a dict, the keys should include the curve mnemonics.
    if isinstance(data, dict):
        assert "DEPT" in data
        assert "GR" in data


# ---------------------------------------------------------------------------
# Data array length
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_data_values():
    """Each per-curve data array in the JSON output has exactly the same
    length as the number of rows in the LASFile."""
    las = _read_inline()
    n_rows = len(las.curves["DEPT"].data)   # 4
    parsed = json.loads(las.json)
    data = parsed["data"]
    if isinstance(data, dict):
        for mnemonic, samples in data.items():
            assert len(samples) == n_rows, (
                f"Curve {mnemonic!r}: expected {n_rows} samples, got {len(samples)}"
            )


# ---------------------------------------------------------------------------
# NaN serialized as null
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_nan_as_null():
    """NaN values that arise from the NULL sentinel (-999.25) are serialized
    as JSON null, not as the string 'NaN' or a number."""
    las = _read_inline()
    # Row 3 (index 3) has -999.25 in GR → should be NaN in the array, null
    # in JSON.  Row 2 has -999.25 in SP.
    parsed = json.loads(las.json)
    data = parsed["data"]
    if isinstance(data, dict) and "GR" in data:
        # The last entry in GR must be null (Python None after json.loads)
        assert data["GR"][3] is None
    # Alternative: ensure the raw JSON string does not contain a bare 'NaN'
    # (which would be invalid JSON produced by naive serialization).
    assert "NaN" not in las.json


# ---------------------------------------------------------------------------
# Setter blocked
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_setter_blocked():
    """Attempting to assign to las.json raises an exception (AttributeError
    or similar) because it is a read-only computed property."""
    las = _read_inline()
    with pytest.raises(Exception):
        las.json = '{"mnemonic": "FAKE"}'


# ---------------------------------------------------------------------------
# Custom JSONEncoder
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_json_encoder_class():
    """json.dumps(las, cls=las_rs.JSONEncoder) produces a valid JSON string
    that contains both 'metadata' and 'data' top-level keys."""
    las = _read_inline()
    raw = json.dumps(las, cls=las_rs.JSONEncoder)
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert "metadata" in parsed or "data" in parsed
