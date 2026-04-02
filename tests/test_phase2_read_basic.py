"""
Phase 2 tests — Basic LAS file reading.

Tests cover ``las_rs.read(file_ref) -> LASFile`` for both LAS 1.2 and 2.0
sample files, verifying header values, curve metadata, and data content.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.
"""

import io
import os

import numpy as np
import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper — mirrors the inline snippet from the spec so tests can also
# be run without conftest.py in a pinch.
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(fn):
    """Return the absolute path to a file under tests/fixtures/."""
    return os.path.join(test_dir, "fixtures", fn)


# ===========================================================================
# LAS 1.2 — sample_v12.las
# ===========================================================================
#
# File facts (from tests/fixtures/v12/sample_v12.las):
#   VERS  = 1.2
#   COMP  = ACME DRILLING CO.
#   WELL  = GAMMA-7 #3
#   STRT  = 500.0 M,  STOP = 502.5 M,  STEP = 0.5 M
#   NULL  = -999.25
#   Curves: DEPT, GR, NPHI, RHOB  (4 curves, 6 depth steps)
#   Params: BHT, BS
#   Other section: free text about calibration and mud weight


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12():
    """Reading a valid LAS 1.2 file returns a LASFile instance."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_version_value():
    """The VERS mnemonic in a LAS 1.2 file has value 1.2."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert float(las.version["VERS"].value) == pytest.approx(1.2)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_well_company():
    """The COMP item in the well section matches the company name in the file."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    # In LAS 1.2 the value is in the *description* field for non-depth items.
    comp = las.well["COMP"].value
    assert "ACME DRILLING" in comp


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_well_name():
    """The WELL item in the well section matches the well name in the file."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    well_name = las.well["WELL"].value
    assert "GAMMA-7" in well_name


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_strt_stop_step():
    """STRT, STOP, and STEP depth values are parsed as correct floats."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert float(las.well["STRT"].value) == pytest.approx(500.0)
    assert float(las.well["STOP"].value) == pytest.approx(502.5)
    assert float(las.well["STEP"].value) == pytest.approx(0.5)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_null_value():
    """The NULL value is parsed as -999.25."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert float(las.well["NULL"].value) == pytest.approx(-999.25)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_curve_count():
    """The file has exactly 4 curves (DEPT, GR, NPHI, RHOB)."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert len(las.curves) == 4


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_curve_mnemonics():
    """Curve mnemonics match the declared order in the ~CURVE section."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    mnemonics = [c.mnemonic for c in las.curves]
    assert mnemonics == ["DEPT", "GR", "NPHI", "RHOB"]


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_data_shape():
    """The data array has shape (6, 4) — 6 depth rows × 4 curves."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    # las.data is a 2-D numpy array with shape (n_rows, n_curves)
    assert las.data.shape == (6, 4)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_first_depth():
    """The first depth value equals STRT (500.0)."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    assert las.curves["DEPT"].data[0] == pytest.approx(500.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_params():
    """The parameter section contains BHT and BS."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    param_mnemonics = [p.mnemonic for p in las.params]
    assert "BHT" in param_mnemonics
    assert "BS" in param_mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_other():
    """The ~OTHER section contains the calibration text from the file."""
    las = las_rs.read(fixture("v12/sample_v12.las"))
    other_text = las.other
    assert "calibrated" in other_text.lower() or "calibrat" in other_text.lower()


# ===========================================================================
# LAS 2.0 — sample_v20.las
# ===========================================================================
#
# File facts (from tests/fixtures/v20/sample_v20.las):
#   VERS  = 2.0
#   COMP  = OCEANIC ENERGY INC.
#   WELL  = DEEP HORIZON #1
#   STRT  = 100.0 FT,  STOP = 110.0 FT,  STEP = 2.0 FT
#   NULL  = -9999.25
#   Curves: DEPT, DT, GR, CALI, SP  (5 curves, 6 rows)
#   Row 0 data: DEPT=100, DT=85.44, GR=28.31, CALI=8.62, SP=-58.76


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v20():
    """Reading a valid LAS 2.0 file returns a LASFile instance."""
    las = las_rs.read(fixture("v20/sample_v20.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v20_version_value():
    """The VERS mnemonic in a LAS 2.0 file has value 2.0."""
    las = las_rs.read(fixture("v20/sample_v20.las"))
    assert float(las.version["VERS"].value) == pytest.approx(2.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v20_curve_count():
    """The LAS 2.0 sample file has exactly 5 curves."""
    las = las_rs.read(fixture("v20/sample_v20.las"))
    assert len(las.curves) == 5


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v20_data_values():
    """Spot-check: first row DT=85.44, GR=28.31 (within floating-point tolerance)."""
    las = las_rs.read(fixture("v20/sample_v20.las"))
    dt_data = las.curves["DT"].data
    gr_data = las.curves["GR"].data
    assert dt_data[0] == pytest.approx(85.44)
    assert gr_data[0] == pytest.approx(28.31)


# ===========================================================================
# Minimal files
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v12_minimal():
    """A stripped-down LAS 1.2 file (no params/other) loads without error."""
    las = las_rs.read(fixture("v12/sample_v12_minimal.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v20_minimal():
    """A stripped-down LAS 2.0 file loads without error."""
    las = las_rs.read(fixture("v20/sample_v20_minimal.las"))
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# Alternative input forms
# ===========================================================================


# Full LAS 1.2 content as a multi-line string.
_SAMPLE_LAS_STRING = """\
~VERSION INFORMATION
 VERS.  1.2 : LAS VERSION 1.2
 WRAP.   NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION BLOCK
 STRT.M  1000.0 : START DEPTH
 STOP.M  1001.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  STRINGTEST INC : COMPANY
 WELL.  STRTEST-1      : WELL
~CURVE INFORMATION BLOCK
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 1000.0  58.20
 1001.0  71.40
"""


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_string():
    """Passing a multi-line LAS string (not a filename) returns a LASFile."""
    las = las_rs.read(_SAMPLE_LAS_STRING)
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(1.2)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_file_object():
    """Passing an open file handle returns a LASFile."""
    with open(fixture("v12/sample_v12.las"), "r") as fh:
        las = las_rs.read(fh)
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# Error cases
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_nonexistent_file():
    """Reading a path that does not exist raises OSError (or a subclass)."""
    with pytest.raises(OSError):
        las_rs.read(fixture("v12/does_not_exist.las"))


@pytest.mark.xfail(reason="not yet implemented")
def test_read_not_a_las_file():
    """Passing garbage content (no ~ sections) raises KeyError."""
    garbage = "this is not\na las file at all\njust random text\n"
    with pytest.raises(KeyError):
        las_rs.read(garbage)
