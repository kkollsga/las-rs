"""
Phase 5f tests — Depth unit detection and conversion.

Covers las.index_unit detection from the STRT header (M, FT, unknown),
depth_m and depth_ft conversion helpers, error on unknown unit, and the
index_unit= override when reading.

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
# Inline LAS helpers — all self-contained, no fixture files needed.
# ---------------------------------------------------------------------------

def _las_meters():
    """Return a LASFile whose depth index is in metres."""
    return las_rs.read("""\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   500.0 : START DEPTH
 STOP.M   502.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  NORDIC PETROLEUM : COMPANY
 WELL.  FJORD-3 #1       : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 500.0   33.11
 501.0   41.55
 502.0   38.72
""")


def _las_feet():
    """Return a LASFile whose depth index is in feet."""
    return las_rs.read("""\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FT  1640.0 : START DEPTH
 STOP.FT  1643.0 : STOP DEPTH
 STEP.FT     1.0 : STEP VALUE
 NULL.   -999.25 : NULL VALUE
 COMP.  GULF COAST ENERGY : COMPANY
 WELL.  LONGHORN-9 #2     : WELL NAME
~CURVE INFORMATION
 DEPT.FT   : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 1640.0   55.21
 1641.0   62.88
 1642.0   49.77
 1643.0   57.30
""")


def _las_unknown_unit():
    """Return a LASFile whose depth index uses an unrecognised unit."""
    return las_rs.read("""\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FATH  100.0 : START DEPTH
 STOP.FATH  102.0 : STOP DEPTH
 STEP.FATH    1.0 : STEP VALUE
 NULL.    -999.25 : NULL VALUE
 COMP.  ABYSSAL SURVEYS : COMPANY
 WELL.  SEAMOUNT-1 #3   : WELL NAME
~CURVE INFORMATION
 DEPT.FATH  : MEASURED DEPTH
 GR  .GAPI  : GAMMA RAY
~ASCII LOG DATA
 100.0   27.44
 101.0   31.19
 102.0   29.88
""")


# Conversion constant
_FT_PER_M = 1.0 / 0.3048   # metres → feet
_M_PER_FT = 0.3048          # feet   → metres


# ===========================================================================
# index_unit detection
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_index_unit_meters():
    """A file with STRT.M in the well section has las.index_unit == 'M'."""
    las = _las_meters()
    assert las.index_unit == "M"


@pytest.mark.xfail(reason="not yet implemented")
def test_index_unit_feet():
    """A file with STRT.FT in the well section has las.index_unit == 'FT'."""
    las = _las_feet()
    assert las.index_unit == "FT"


@pytest.mark.xfail(reason="not yet implemented")
def test_index_unit_none():
    """A file with an unrecognised depth unit (e.g. FATH) has
    las.index_unit == None."""
    las = _las_unknown_unit()
    assert las.index_unit is None


# ===========================================================================
# depth_m — metre output
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_m_from_meters():
    """depth_m on a metric file returns the index values unchanged."""
    las = _las_meters()
    expected = las.curves["DEPT"].data
    np.testing.assert_array_almost_equal(las.depth_m, expected)


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_m_from_feet():
    """depth_m on a feet-indexed file returns values converted by * 0.3048."""
    las = _las_feet()
    depth_ft = las.curves["DEPT"].data
    expected_m = depth_ft * _M_PER_FT
    np.testing.assert_array_almost_equal(las.depth_m, expected_m, decimal=4)


# ===========================================================================
# depth_ft — feet output
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_ft_from_feet():
    """depth_ft on a feet-indexed file returns the index values unchanged."""
    las = _las_feet()
    expected = las.curves["DEPT"].data
    np.testing.assert_array_almost_equal(las.depth_ft, expected)


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_ft_from_meters():
    """depth_ft on a metric file returns values converted by / 0.3048."""
    las = _las_meters()
    depth_m = las.curves["DEPT"].data
    expected_ft = depth_m * _FT_PER_M
    np.testing.assert_array_almost_equal(las.depth_ft, expected_ft, decimal=4)


# ===========================================================================
# Error on unknown unit
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unknown_raises():
    """Calling depth_m on a LASFile with an unrecognised depth unit raises
    las_rs.LASUnknownUnitError (or a subclass of Exception)."""
    las = _las_unknown_unit()
    with pytest.raises((las_rs.LASUnknownUnitError, Exception)):
        _ = las.depth_m


# ===========================================================================
# index_unit override at read time
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_force_index_unit():
    """Passing index_unit='m' to las_rs.read() overrides the auto-detected
    unit; las.index_unit should reflect the forced value."""
    # Read the feet file but force the unit to metres.
    las = las_rs.read("""\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FT  5000.0 : START DEPTH
 STOP.FT  5002.0 : STOP DEPTH
 STEP.FT     1.0 : STEP VALUE
 NULL.   -999.25 : NULL VALUE
 COMP.  SUMMIT DRILLING : COMPANY
 WELL.  HIGHPEAK-2 #1  : WELL NAME
~CURVE INFORMATION
 DEPT.FT   : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 5000.0   44.10
 5001.0   52.37
 5002.0   48.95
""", index_unit="m")
    # The forced unit should be stored (case-insensitive comparison)
    assert las.index_unit is not None
    assert las.index_unit.lower() == "m"
