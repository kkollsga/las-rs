"""
Phase 5 extended: Depth unit edge cases.

Covers alias spellings for feet ("FEET", "F"), lowercase metres ("m"), the
tenth-of-an-inch unit (".1IN"), conflicting header vs. curve units producing
None index_unit, and depth_m conversion from .1IN.

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
# Inline LAS builder helpers
# ---------------------------------------------------------------------------

def _make_las(strt_unit, curve_unit, strt_val=200.0, stop_val=202.0, step_val=1.0):
    """Build a minimal 3-row LAS string with the given depth units."""
    return """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.{su}  {strt} : START DEPTH
 STOP.{su}  {stop} : STOP DEPTH
 STEP.{su}   {step} : STEP VALUE
 NULL. -999.25     : NULL VALUE
 COMP.  DEEPROCK PETROLEUM : COMPANY
 WELL.  TUNGSTEN-6 #3      : WELL NAME
~CURVE INFORMATION
 DEPT.{cu}  : MEASURED DEPTH
 RES .OHM   : RESISTIVITY
~ASCII LOG DATA
 {strt}   12.50
 {mid}    14.30
 {stop}   11.80
""".format(
        su=strt_unit,
        cu=curve_unit,
        strt=strt_val,
        mid=strt_val + step_val,
        stop=stop_val,
        step=step_val,
    )


# ---------------------------------------------------------------------------
# .1IN index values — 120 units per inch, 12 per foot
# index values are in tenths of an inch: 1200, 1201, 1202
# depth in feet  = index / 120
# depth in metres = (index / 120) * 0.3048
# ---------------------------------------------------------------------------

_LAS_POINT_ONE_INCH = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT..1IN   1200 : START DEPTH
 STOP..1IN   1202 : STOP DEPTH
 STEP..1IN      1 : STEP VALUE
 NULL.   -999.25  : NULL VALUE
 COMP.  CORETEK SURVEYS INC : COMPANY
 WELL.  PINPOINT-2 #1       : WELL NAME
~CURVE INFORMATION
 DEPT..1IN  : MEASURED DEPTH
 PORO.V/V   : POROSITY
~ASCII LOG DATA
 1200   0.321
 1201   0.305
 1202   0.287
"""

_M_PER_FT = 0.3048


# ===========================================================================
# 1. "FEET" spelt out is detected as "FT"
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unit_feet_spelled_out():
    """A file whose STRT unit is the word 'FEET' should have index_unit == 'FT'
    after normalisation, not None and not 'FEET'."""
    las = las_rs.read(_make_las("FEET", "FEET", strt_val=1000.0, stop_val=1002.0))
    assert las.index_unit == "FT"


# ===========================================================================
# 2. Single-letter "F" is detected as "FT"
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unit_f():
    """A file whose STRT unit is the single letter 'F' should have
    index_unit == 'FT' after normalisation."""
    las = las_rs.read(_make_las("F", "F", strt_val=500.0, stop_val=502.0))
    assert las.index_unit == "FT"


# ===========================================================================
# 3. Lowercase "m" is detected as "M"
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unit_lowercase_m():
    """A file whose STRT unit is lowercase 'm' should have index_unit == 'M'
    (case-normalised to uppercase)."""
    las = las_rs.read(_make_las("m", "m", strt_val=300.0, stop_val=302.0))
    assert las.index_unit == "M"


# ===========================================================================
# 4. ".1IN" unit is detected and depth_ft converts correctly
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unit_point_one_inch():
    """A file with unit '.1IN' has its index_unit recognised (not None);
    depth_ft returns index / 120 (tenths-of-an-inch to feet)."""
    las = las_rs.read(_LAS_POINT_ONE_INCH)
    # index_unit must be recognised (the exact string may vary by impl)
    assert las.index_unit is not None
    # depth in feet: index / 120
    index_values = las.curves["DEPT"].data  # [1200, 1201, 1202]
    expected_ft = index_values / 120.0
    np.testing.assert_array_almost_equal(las.depth_ft, expected_ft, decimal=5)


# ===========================================================================
# 5. Conflicting header vs. curve units => index_unit is None
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_unit_inconsistent_none():
    """When the STRT header unit (M) disagrees with the first curve unit (FT)
    the implementation cannot resolve the conflict and index_unit is None."""
    las = las_rs.read(_make_las("M", "FT", strt_val=400.0, stop_val=402.0))
    assert las.index_unit is None


# ===========================================================================
# 6. depth_m converts from .1IN correctly
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_depth_m_from_point_one_inch():
    """depth_m on a .1IN file returns (index / 120) * 0.3048 — first convert
    tenths-of-an-inch to feet, then feet to metres."""
    las = las_rs.read(_LAS_POINT_ONE_INCH)
    index_values = las.curves["DEPT"].data  # [1200, 1201, 1202]
    expected_m = (index_values / 120.0) * _M_PER_FT
    np.testing.assert_array_almost_equal(las.depth_m, expected_m, decimal=5)
