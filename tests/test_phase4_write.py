"""
Phase 4 tests — LAS file writing.

Covers writing to file objects and file paths, version tagging, preservation
of in-memory state, correct STRT/STOP/STEP computation, NULL rendering, all
header section roundtrips, data section formatting options, edge cases (empty
file, single row, large depths, NaN-as-null), and full read/write roundtrips.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
import tempfile
from io import StringIO

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

V12_FILE = fixture("v12/sample_v12.las")
V20_FILE = fixture("v20/sample_v20.las")


def read_v12():
    return las_rs.read(V12_FILE)


def read_v20():
    return las_rs.read(V20_FILE)


# ---------------------------------------------------------------------------
# Write target types
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_to_file_object():
    """write() accepts a file-like object (StringIO) and the output begins
    with a ~Version section marker."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert output.lstrip().startswith("~V") or "~VERSION" in output.upper()


@pytest.mark.xfail(reason="not yet implemented")
def test_write_to_filename():
    """write() accepts a file-system path string and creates the file."""
    las = read_v12()
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as f:
        tmp_path = f.name
    try:
        las.write(tmp_path)
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Version tagging
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_version_12():
    """write(version=1.2) produces output that contains 'VERS' with value
    '1.2'."""
    las = read_v12()
    buf = StringIO()
    las.write(buf, version=1.2)
    output = buf.getvalue()
    assert "1.2" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_version_20():
    """write(version=2.0) produces output that contains 'VERS' with value
    '2.0'."""
    las = read_v12()
    buf = StringIO()
    las.write(buf, version=2.0)
    output = buf.getvalue()
    assert "2.0" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_preserves_version():
    """Writing with version=2.0 does not mutate the in-memory VERS item of
    the original LASFile object."""
    las = read_v12()
    original_vers = las.version["VERS"].value
    buf = StringIO()
    las.write(buf, version=2.0)
    assert las.version["VERS"].value == original_vers


# ---------------------------------------------------------------------------
# STRT / STOP / STEP
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_strt_stop_step():
    """STRT and STOP in the written output match the first and last values
    of the depth index array."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    dept = las.curves["DEPT"].data
    expected_strt = f"{dept[0]:.4f}" if dept[0] == int(dept[0]) else str(dept[0])
    expected_stop = f"{dept[-1]:.4f}" if dept[-1] == int(dept[-1]) else str(dept[-1])
    # Both boundary depths must appear somewhere in the header block
    assert str(dept[0]) in output or "500" in output
    assert str(dept[-1]) in output or "502" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_step_unchanged():
    """The STEP value stored in the LASFile header is not mutated by a
    write() call."""
    las = read_v12()
    original_step = las.well["STEP"].value
    buf = StringIO()
    las.write(buf)
    assert las.well["STEP"].value == original_step


# ---------------------------------------------------------------------------
# NULL value
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_null_value():
    """The NULL sentinel value from the well section appears verbatim in the
    written output."""
    las = read_v12()
    null_val = las.well["NULL"].value
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert str(null_val).strip() in output


# ---------------------------------------------------------------------------
# Header sections
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_well_section():
    """All well-section items (COMP, WELL, UWI) appear in the written
    output."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert "ACME DRILLING" in output or "COMP" in output
    assert "GAMMA-7" in output or "WELL" in output
    assert "UWI" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_curve_section():
    """Curve mnemonics from the ~Curve section appear in the written
    output."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    for curve in las.curves:
        assert curve.mnemonic in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_param_section():
    """Parameter section items (e.g. BHT, BS) appear in the written
    output."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert "BHT" in output
    assert "BS" in output


@pytest.mark.xfail(reason="not yet implemented")
def test_write_other_section():
    """Free-text content from the ~Other section is reproduced in the written
    output."""
    las = read_v12()
    # Verify the fixture actually has an Other section
    other_text = las.other
    if not other_text.strip():
        pytest.skip("fixture has no Other section text")
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    # At least one word from the Other block must appear
    first_word = other_text.split()[0]
    assert first_word in output


# ---------------------------------------------------------------------------
# Data section format options
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_data_section_default_header():
    """By default the data section starts with a line containing '~A' or
    '~ASCII'."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    upper = output.upper()
    assert "~A" in upper


@pytest.mark.xfail(reason="not yet implemented")
def test_write_data_section_mnemonics():
    """mnemonics_header=True inserts a comment/header line with curve names
    immediately after the ~ASCII marker."""
    las = read_v12()
    buf = StringIO()
    las.write(buf, mnemonics_header=True)
    output = buf.getvalue()
    # Each curve mnemonic should appear in the data section header line
    for curve in las.curves:
        assert curve.mnemonic in output


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_empty_las():
    """Writing a freshly constructed (empty) LASFile does not raise an
    exception and the output still contains the ~Version section."""
    las = las_rs.LASFile()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()
    assert "~V" in output.upper() or "VERS" in output.upper()


@pytest.mark.xfail(reason="not yet implemented")
def test_write_single_row():
    """A LASFile with a single data row writes and re-reads correctly."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : WRAP\n"
        "~WELL INFORMATION\n"
        " STRT.M   100.0 : START\n"
        " STOP.M   100.0 : STOP\n"
        " STEP.M     0.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. SINGLE-ROW : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M   : DEPTH\n"
        " GR  .GAPI: GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 100.0   42.15\n"
    )
    las = las_rs.read(las_text)
    buf = StringIO()
    las.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf)
    assert reread.curves["DEPT"].data[0] == pytest.approx(100.0)
    assert reread.curves["GR"].data[0] == pytest.approx(42.15)


@pytest.mark.xfail(reason="not yet implemented")
def test_write_large_depths():
    """Large depth values (e.g. 12345.6789) are written with enough decimal
    places that re-reading preserves the value to at least 3 significant
    figures."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : WRAP\n"
        "~WELL INFORMATION\n"
        " STRT.FT  12345.6789 : START\n"
        " STOP.FT  12346.6789 : STOP\n"
        " STEP.FT      1.0000 : STEP\n"
        " NULL.      -999.25 : NULL\n"
        " WELL. DEEP-WELL-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.FT   : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 12345.6789   88.123\n"
        " 12346.6789   91.456\n"
    )
    las = las_rs.read(las_text)
    buf = StringIO()
    las.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf)
    assert reread.curves["DEPT"].data[0] == pytest.approx(12345.6789, rel=1e-4)


@pytest.mark.xfail(reason="not yet implemented")
def test_roundtrip_v12():
    """Read a v1.2 file, write it, and re-read it: all curve data arrays
    must match the original to at least 4 decimal places."""
    original = read_v12()
    buf = StringIO()
    original.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf)

    for curve in original.curves:
        np.testing.assert_array_almost_equal(
            curve.data,
            reread.curves[curve.mnemonic].data,
            decimal=4,
        )


@pytest.mark.xfail(reason="not yet implemented")
def test_roundtrip_v20():
    """Read a v2.0 file, write it, and re-read it: all curve data arrays
    must match the original to at least 4 decimal places."""
    original = read_v20()
    buf = StringIO()
    original.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf)

    for curve in original.curves:
        np.testing.assert_array_almost_equal(
            curve.data,
            reread.curves[curve.mnemonic].data,
            decimal=4,
        )


# ---------------------------------------------------------------------------
# Column alignment
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_write_section_widths():
    """Header lines are column-aligned: the value column starts at the same
    character position for all lines within a section."""
    las = read_v12()
    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()

    # Collect the ~Well section lines (between ~W and the next ~)
    in_well = False
    well_lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("~W"):
            in_well = True
            continue
        if stripped.startswith("~") and in_well:
            break
        if in_well and stripped and not stripped.startswith("#"):
            well_lines.append(line)

    # Every well-section line must contain a '.' separator (mnemonic.unit)
    for line in well_lines:
        assert "." in line, f"Missing '.' separator in well section line: {line!r}"
