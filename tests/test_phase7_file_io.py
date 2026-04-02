"""
Phase 7: File I/O — different input sources (pathlib, strings, file objects, URLs).

Covers reading LAS content from a string file path, a ``pathlib.Path``, an open
file handle, and a raw multi-line LAS string.  Also tests error handling for
non-existent files and LiDAR LASF magic bytes, plus writing to both file handles
and string paths.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.

Note: tests that write to disk use the ``tmp_path`` pytest fixture so they never
leave artefacts behind.
"""

import io
import os
import pathlib

import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Minimal inline LAS 2.0 string reused across several tests.
# ---------------------------------------------------------------------------

_MINIMAL_LAS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  800.0 : START DEPTH
 STOP.M  802.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -9999.25 : NULL VALUE
 COMP.  FILEIO TEST CO.  : COMPANY
 WELL.  FILEIO-1          : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 800.0  34.12
 801.0  51.87
 802.0  66.44
"""


def _write_minimal_las(path: str) -> None:
    """Helper: write the minimal LAS string to *path* on disk."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_MINIMAL_LAS)


# ===========================================================================
# Reading from different source types
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_filename(tmp_path):
    """las_rs.read() accepts a plain str file path and returns a LASFile."""
    p = tmp_path / "fileio_test.las"
    p.write_text(_MINIMAL_LAS, encoding="utf-8")
    las = las_rs.read(str(p))
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(2.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_pathlib(tmp_path):
    """las_rs.read() accepts a pathlib.Path and returns a LASFile."""
    p = tmp_path / "fileio_pathlib.las"
    p.write_text(_MINIMAL_LAS, encoding="utf-8")
    las = las_rs.read(pathlib.Path(p))
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(2.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_file_object(tmp_path):
    """las_rs.read() accepts an open text file handle and returns a LASFile."""
    p = tmp_path / "fileio_handle.las"
    p.write_text(_MINIMAL_LAS, encoding="utf-8")
    with open(str(p), "r", encoding="utf-8") as fh:
        las = las_rs.read(fh)
    assert isinstance(las, las_rs.LASFile)
    assert float(las.well["STRT"].value) == pytest.approx(800.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_from_string_content():
    """las_rs.read() accepts a multi-line LAS string (not a file path) and
    parses it directly.  The string contains a newline so it cannot be a
    file path on any OS."""
    las = las_rs.read(_MINIMAL_LAS)
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(2.0)
    assert las.curves["DEPT"].data[0] == pytest.approx(800.0)
    assert las.curves["GR"].data[1] == pytest.approx(51.87)


# ===========================================================================
# Error cases
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_nonexistent_raises():
    """las_rs.read() raises OSError when the path does not exist."""
    with pytest.raises(OSError):
        las_rs.read(fixture("v20", "does_not_exist_7x9q.las"))


@pytest.mark.xfail(reason="not yet implemented")
def test_lidar_file_rejected(tmp_path):
    """A file whose first four bytes are 'LASF' (LiDAR LAS format magic) is
    rejected with an IOError (or a subclass thereof)."""
    lidar_path = tmp_path / "fake_lidar.las"
    # Write the LASF magic followed by arbitrary bytes.
    lidar_path.write_bytes(b"LASF" + b"\x00" * 64)
    with pytest.raises(IOError):
        las_rs.read(str(lidar_path))


# ===========================================================================
# Writing
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_to_file_object():
    """las.write() accepts an open StringIO / file handle and writes valid LAS
    content that begins with a ~Version section marker."""
    las = las_rs.read(_MINIMAL_LAS)
    buf = io.StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert output.lstrip().startswith("~V") or "~VERSION" in output.upper()
    # The well name we loaded should survive the write.
    assert "FILEIO-1" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_to_filename(tmp_path):
    """las.write() accepts a str file path, creates the file, and the file is
    non-empty and begins with valid LAS content."""
    las = las_rs.read(_MINIMAL_LAS)
    out_path = str(tmp_path / "written_output.las")
    las.write(out_path)

    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0

    # Re-reading the written file should give back consistent header data.
    reread = las_rs.read(out_path)
    assert isinstance(reread, las_rs.LASFile)
    assert float(reread.version["VERS"].value) == pytest.approx(2.0)
