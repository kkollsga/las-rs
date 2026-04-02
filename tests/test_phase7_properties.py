"""
Phase 7b: LASFile property accessors — version, well, curves, params, other,
header, data, index.

Verifies the property-based API surface of ``LASFile``: each property getter
returns the expected type, each setter stores the value in the underlying
``sections`` dict, and helper methods (``update_start_stop_step``,
``curvesdict``) behave correctly.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.
"""

import os

import numpy as np
import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Inline LAS 2.0 string used to build a populated LASFile for most tests.
# Values are original to this project's test suite.
# ---------------------------------------------------------------------------

_LAS_CONTENT = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  3000.0 : START DEPTH
 STOP.M  3004.0 : STOP DEPTH
 STEP.M     2.0 : STEP VALUE
 NULL. -9999.25 : NULL VALUE
 COMP.  PROPS TEST LTD.  : COMPANY
 WELL.  PROPSWELL-3       : WELL NAME
 UWI .  300-22-333-44W5  : UNIQUE WELL ID
~CURVE INFORMATION
 DEPT.M      : DEPTH
 DT  .US/M   : SONIC TRANSIT TIME
 PORO.V/V    : POROSITY
~PARAMETER INFORMATION
 BHT .DEGC  155.0 : BOTTOM HOLE TEMPERATURE
 MUD .      OBM   : MUD TYPE
~OTHER
 Processed by PropsTest pipeline v2.
~ASCII LOG DATA
 3000.0  312.45  0.182
 3002.0  298.11  0.196
 3004.0  325.67  0.174
"""


def _read_las():
    """Return a populated LASFile from the inline string."""
    return las_rs.read(_LAS_CONTENT)


# ===========================================================================
# .version property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_version_property():
    """las.version returns the SectionItems for the Version section."""
    las = _read_las()
    version = las.version
    # Should be indexable by mnemonic and contain VERS.
    assert version["VERS"] is not None
    assert float(version["VERS"].value) == pytest.approx(2.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_well_property():
    """las.well returns the SectionItems for the Well section."""
    las = _read_las()
    well = las.well
    assert well["COMP"] is not None
    assert "PROPS TEST" in well["COMP"].value or "PROPS TEST" in well["COMP"].descr


@pytest.mark.xfail(reason="not yet implemented")
def test_curves_property():
    """las.curves returns the SectionItems for the Curves section."""
    las = _read_las()
    curves = las.curves
    mnemonics = [c.mnemonic for c in curves]
    assert "DEPT" in mnemonics
    assert "DT" in mnemonics
    assert "PORO" in mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_params_property():
    """las.params returns the SectionItems for the Parameter section."""
    las = _read_las()
    params = las.params
    param_mnemonics = [p.mnemonic for p in params]
    assert "BHT" in param_mnemonics
    assert "MUD" in param_mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_other_property():
    """las.other returns the free-text content of the ~Other section as a
    string."""
    las = _read_las()
    other = las.other
    assert isinstance(other, str)
    assert "PropsTest" in other or "pipeline" in other.lower()


@pytest.mark.xfail(reason="not yet implemented")
def test_other_setter():
    """Assigning a string to las.other updates sections['Other']."""
    las = _read_las()
    las.other = "New other text for unit testing."
    assert "New other text" in las.sections["Other"]


# ===========================================================================
# .header property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_header_property():
    """las.header returns the full sections dict (all named sections)."""
    las = _read_las()
    header = las.header
    assert isinstance(header, dict)
    assert "Version" in header
    assert "Well" in header
    assert "Curves" in header


# ===========================================================================
# .data property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_data_property():
    """las.data returns a 2-D numpy array with shape (n_rows, n_curves).

    The inline file has 3 rows and 3 curves (DEPT, DT, PORO).
    """
    las = _read_las()
    data = las.data
    assert isinstance(data, np.ndarray)
    assert data.ndim == 2
    assert data.shape == (3, 3)


@pytest.mark.xfail(reason="not yet implemented")
def test_data_setter():
    """Assigning to las.data calls set_data() and updates the stored array."""
    las = _read_las()
    new_data = np.array(
        [[3000.0, 310.0, 0.190],
         [3002.0, 295.0, 0.200],
         [3004.0, 320.0, 0.180]],
        dtype=float,
    )
    las.data = new_data
    np.testing.assert_array_almost_equal(las.data, new_data)


# ===========================================================================
# .index property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_index_property():
    """las.index returns the data array of the first curve (the depth index).

    For the inline file the first curve is DEPT with values [3000, 3002, 3004].
    """
    las = _read_las()
    index = las.index
    assert isinstance(index, np.ndarray)
    np.testing.assert_array_almost_equal(index, [3000.0, 3002.0, 3004.0])


# ===========================================================================
# .curvesdict
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_curvesdict():
    """las.curvesdict returns a dict mapping mnemonic strings to CurveItem
    objects."""
    las = _read_las()
    cd = las.curvesdict
    assert isinstance(cd, dict)
    assert set(cd.keys()) == {"DEPT", "DT", "PORO"}
    assert isinstance(cd["DT"], las_rs.CurveItem)
    assert cd["DT"].unit == "US/M"


# ===========================================================================
# update_start_stop_step
# ===========================================================================


