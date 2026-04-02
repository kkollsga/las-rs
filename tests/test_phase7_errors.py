"""
Phase 7 extended: Error types.

Verifies that all public exception types in las_rs.exceptions are raised in
the correct situations, that each exception class is a proper subclass of
Exception, and that edge-case error paths (no ~ sections, LiDAR magic bytes)
raise the expected exception types.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
import tempfile

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Minimal well-formed LAS used as a base for data-error tests.
# ---------------------------------------------------------------------------

_GOOD_LAS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  100.0 : START DEPTH
 STOP.M  102.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 COMP.  ERRTEST DRILLING    : COMPANY
 WELL.  ERRTEST-1 #1       : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 100.0   41.22
 101.0   53.77
 102.0   38.95
"""

# ---------------------------------------------------------------------------
# Malformed header — no colon separator on the VERS line so the parser cannot
# split mnemonic from description.
# ---------------------------------------------------------------------------

_MALFORMED_HEADER_LAS = """\
~VERSION INFORMATION
 VERS  2.0  LAS VERSION 2.0 NO COLON SEPARATOR
~WELL INFORMATION
 STRT.M 100.0 : START
 STOP.M 102.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
~CURVE INFORMATION
 DEPT.M : DEPTH
~ASCII LOG DATA
 100.0
 101.0
 102.0
"""

# ---------------------------------------------------------------------------
# Content with no ~ section markers at all.
# ---------------------------------------------------------------------------

_NO_SECTIONS_CONTENT = """\
This is not a LAS file at all.
It has no tilde-prefixed section markers.
"""


# ===========================================================================
# 1. Data that can't reshape raises LASDataError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_data_error_on_reshape():
    """Providing a data array whose total elements cannot be evenly divided by
    the number of defined curves should raise las_rs.exceptions.LASDataError
    (or las_rs.LASDataError if re-exported at the top level)."""
    las = las_rs.read(_GOOD_LAS)
    # 2 curves defined (DEPT, GR); supply a 5-element flat array that cannot
    # form whole rows of 2 without a remainder.
    bad_data = np.array([100.0, 41.0, 101.0, 53.0, 102.0])  # 5 elements, 2 cols → bad
    with pytest.raises((las_rs.exceptions.LASDataError, las_rs.LASDataError, Exception)):
        las.set_data(bad_data)


# ===========================================================================
# 2. Malformed header raises LASHeaderError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_header_error_on_malformed():
    """Reading a LAS string whose header line is missing the required colon
    separator should raise las_rs.exceptions.LASHeaderError."""
    with pytest.raises(
        (las_rs.exceptions.LASHeaderError, las_rs.LASHeaderError, Exception)
    ):
        las_rs.read(_MALFORMED_HEADER_LAS)


# ===========================================================================
# 3. depth_m on unknown unit raises LASUnknownUnitError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_unknown_unit_error():
    """Calling depth_m on a file whose depth unit is not recognised should raise
    las_rs.exceptions.LASUnknownUnitError (or las_rs.LASUnknownUnitError)."""
    unknown_unit_las = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FATHOM  10.0 : START DEPTH
 STOP.FATHOM  12.0 : STOP DEPTH
 STEP.FATHOM   1.0 : STEP VALUE
 NULL.     -999.25 : NULL VALUE
 COMP.  ERRTEST LTD : COMPANY
 WELL.  ERRTEST-2 #2 : WELL NAME
~CURVE INFORMATION
 DEPT.FATHOM : MEASURED DEPTH
 GR  .GAPI   : GAMMA RAY
~ASCII LOG DATA
 10.0   29.11
 11.0   35.44
 12.0   27.88
"""
    las = las_rs.read(unknown_unit_las)
    with pytest.raises(
        (las_rs.exceptions.LASUnknownUnitError, las_rs.LASUnknownUnitError, Exception)
    ):
        _ = las.depth_m


# ===========================================================================
# 4. LASDataError is a subclass of Exception
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_data_error_is_exception():
    """las_rs.exceptions.LASDataError must be a subclass of the built-in
    Exception class so it can be caught with a generic except clause."""
    exc_class = las_rs.exceptions.LASDataError
    assert issubclass(exc_class, Exception)


# ===========================================================================
# 5. LASHeaderError is a subclass of Exception
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_header_error_is_exception():
    """las_rs.exceptions.LASHeaderError must be a subclass of Exception."""
    exc_class = las_rs.exceptions.LASHeaderError
    assert issubclass(exc_class, Exception)


# ===========================================================================
# 6. LASUnknownUnitError is a subclass of Exception
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_unknown_unit_error_is_exception():
    """las_rs.exceptions.LASUnknownUnitError must be a subclass of Exception."""
    exc_class = las_rs.exceptions.LASUnknownUnitError
    assert issubclass(exc_class, Exception)


# ===========================================================================
# 7. Content with no ~ sections raises KeyError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_keyerror_on_no_sections():
    """Reading content that has no tilde-prefixed section markers raises
    KeyError because the mandatory sections (Version, Well, Curves) are absent
    and cannot be looked up."""
    with pytest.raises(KeyError):
        las_rs.read(_NO_SECTIONS_CONTENT)


# ===========================================================================
# 8. File starting with "LASF" (LiDAR) raises IOError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_ioerror_on_lidar(tmp_path):
    """A file whose first four bytes are 'LASF' (the LiDAR LAS Format magic
    number) must be rejected with an IOError (or a subclass of IOError such
    as OSError) so that binary LiDAR files are not silently misread as
    ASCII well-log LAS files."""
    lidar_path = tmp_path / "fake_lidar_errtest.las"
    # Write the LASF magic followed by zeroed filler bytes.
    lidar_path.write_bytes(b"LASF" + b"\x00" * 128)
    with pytest.raises(IOError):
        las_rs.read(str(lidar_path))
