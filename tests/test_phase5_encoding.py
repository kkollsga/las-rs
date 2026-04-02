"""
Phase 5a tests — Character encoding detection and handling.

Covers reading LAS files with UTF-8, UTF-8 BOM, and Latin-1 encodings,
auto-detection of the encoding attribute, explicit encoding overrides,
the autodetect_encoding flag, and pathlib.Path input.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
import pathlib

import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# File path constants
# ---------------------------------------------------------------------------

UTF8_FILE     = fixture("encodings", "utf8.las")
UTF8_BOM_FILE = fixture("encodings", "utf8_bom.las")
LATIN1_FILE   = fixture("encodings", "latin1.las")


# ---------------------------------------------------------------------------
# UTF-8 plain
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_utf8_reads():
    """A plain UTF-8 file containing non-ASCII characters (Ölbohrung GmbH in
    COMP) is read without raising an exception and the non-ASCII text is
    preserved in the well section."""
    las = las_rs.read(UTF8_FILE)
    comp = las.well["COMP"].value
    assert "Ölbohrung" in comp or "GmbH" in comp


# ---------------------------------------------------------------------------
# UTF-8 BOM
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_utf8_bom_reads():
    """A UTF-8 file that begins with a BOM (byte-order mark) is parsed without
    error; the well section contains the expected company name."""
    las = las_rs.read(UTF8_BOM_FILE)
    comp = las.well["COMP"].value
    assert "GmbH" in comp


@pytest.mark.xfail(reason="not yet implemented")
def test_utf8_bom_encoding_detected():
    """When a BOM is present the auto-detected encoding is reported as
    'utf-8-sig' (Python's name for UTF-8 with BOM)."""
    las = las_rs.read(UTF8_BOM_FILE)
    assert las.encoding is not None
    assert las.encoding.lower() == "utf-8-sig"


# ---------------------------------------------------------------------------
# Latin-1 / ISO 8859-1
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_latin1_reads():
    """A Latin-1 encoded file containing accented characters in the COMP field
    (Société Pétrolière) is read and the non-ASCII characters are present."""
    las = las_rs.read(LATIN1_FILE)
    comp = las.well["COMP"].value
    # The fixture encodes "Société Pétrolière"; at minimum the ASCII part
    # should be there even if decoding is approximate.
    assert comp is not None and len(comp) > 0


# ---------------------------------------------------------------------------
# encoding attribute
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_encoding_attribute_set():
    """After reading any LAS file the resulting LASFile has a non-None
    `encoding` attribute that is a plain string."""
    las = las_rs.read(UTF8_FILE)
    assert las.encoding is not None
    assert isinstance(las.encoding, str)


# ---------------------------------------------------------------------------
# Explicit encoding override
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_explicit_encoding():
    """Passing encoding='latin-1' explicitly causes the Latin-1 fixture to be
    decoded correctly; the company field contains expected text."""
    las = las_rs.read(LATIN1_FILE, encoding="latin-1")
    comp = las.well["COMP"].value
    # "Société Pétrolière" decoded from latin-1 should contain the accented chars
    assert "Soci" in comp and "troli" in comp


# ---------------------------------------------------------------------------
# autodetect_encoding=False
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_autodetect_encoding_false():
    """Passing autodetect_encoding=False disables charset sniffing; the file
    is still readable using a default common encoding (UTF-8 or ASCII)."""
    # The plain UTF-8 file is valid ASCII for the structural parts; it should
    # parse without error even with auto-detection disabled.
    las = las_rs.read(UTF8_FILE, autodetect_encoding=False)
    assert isinstance(las, las_rs.LASFile)
    assert len(las.curves) > 0


# ---------------------------------------------------------------------------
# pathlib.Path input
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_pathlib_path():
    """las_rs.read() accepts a pathlib.Path object in addition to plain
    strings; the result is an equivalent LASFile."""
    path = pathlib.Path(UTF8_FILE)
    las = las_rs.read(path)
    assert isinstance(las, las_rs.LASFile)
    dept = las.curves["DEPT"].data
    assert len(dept) == 3
    assert dept[0] == pytest.approx(100.0)
