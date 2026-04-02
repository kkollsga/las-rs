"""Phase 5 extended: Encoding edge cases."""

import os
import pathlib

import pytest

import las_rs

test_dir = os.path.dirname(__file__)
ENCODINGS_DIR = os.path.join(test_dir, "fixtures", "encodings")


# ---------------------------------------------------------------------------
# Minimal LAS content helpers
# ---------------------------------------------------------------------------

# ASCII-safe LAS text used as the body for all encoding fixture files.
_LAS_ASCII_BODY = (
    "~VERSION INFORMATION\n"
    " VERS.   2.0 : LAS VERSION 2.0\n"
    " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
    "~WELL INFORMATION\n"
    " STRT.M   500.0 : START DEPTH\n"
    " STOP.M   502.0 : STOP DEPTH\n"
    " STEP.M     1.0 : STEP VALUE\n"
    " NULL. -999.25  : NULL VALUE\n"
    " COMP.  Bohrinsel AG       : COMPANY\n"
    " WELL.  NORDKAP-3          : WELL NAME\n"
    "~CURVE INFORMATION\n"
    " DEPT.M    : MEASURED DEPTH\n"
    " GR  .GAPI : GAMMA RAY\n"
    "~ASCII LOG DATA\n"
    " 500.0   55.10\n"
    " 501.0   63.44\n"
    " 502.0   48.77\n"
)


def _ensure_fixture(filename, content_bytes):
    """Write a fixture file if it does not already exist."""
    path = os.path.join(ENCODINGS_DIR, filename)
    if not os.path.exists(path):
        os.makedirs(ENCODINGS_DIR, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content_bytes)
    return path


def _utf16_le_bom_bytes():
    return _LAS_ASCII_BODY.encode("utf-16-le")


def _utf16_be_bom_bytes():
    return _LAS_ASCII_BODY.encode("utf-16-be")


# Pre-build fixture files at import time so they are ready before any test runs.
_UTF16_LE_BOM_FILE = _ensure_fixture(
    "utf16_le_bom.las",
    b"\xff\xfe" + _LAS_ASCII_BODY.encode("utf-16-le"),
)
_UTF16_BE_BOM_FILE = _ensure_fixture(
    "utf16_be_bom.las",
    b"\xfe\xff" + _LAS_ASCII_BODY.encode("utf-16-be"),
)
_UTF16_LE_FILE = _ensure_fixture(
    "utf16_le_explicit.las",
    _LAS_ASCII_BODY.encode("utf-16-le"),
)

# Latin-1 file with a non-ASCII byte in the COMP field.
_LATIN1_EXTENDED_BODY = _LAS_ASCII_BODY.replace("Bohrinsel AG", "P\xe9trolif\xe8re SA")
_LATIN1_BAD_FILE = _ensure_fixture(
    "latin1_bad_bytes.las",
    _LATIN1_EXTENDED_BODY.encode("latin-1"),
)


# ---------------------------------------------------------------------------
# 1. test_utf16_le_bom
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_utf16_le_bom():
    """A UTF-16 LE file that starts with the LE BOM (0xFF 0xFE) is read
    without error and the WELL name is preserved."""
    las = las_rs.read(_UTF16_LE_BOM_FILE)
    assert isinstance(las, las_rs.LASFile)
    well = las.well["WELL"].value
    assert "NORDKAP" in well


# ---------------------------------------------------------------------------
# 2. test_utf16_be_bom
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_utf16_be_bom():
    """A UTF-16 BE file that starts with the BE BOM (0xFE 0xFF) is read
    without error and the WELL name is preserved."""
    las = las_rs.read(_UTF16_BE_BOM_FILE)
    assert isinstance(las, las_rs.LASFile)
    well = las.well["WELL"].value
    assert "NORDKAP" in well


# ---------------------------------------------------------------------------
# 3. test_utf16_le_explicit
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_utf16_le_explicit():
    """Passing encoding='UTF-16-LE' explicitly reads a raw UTF-16 LE file
    (no BOM) without error."""
    las = las_rs.read(_UTF16_LE_FILE, encoding="UTF-16-LE")
    assert isinstance(las, las_rs.LASFile)
    dept = las.curves["DEPT"].data
    assert len(dept) == 3


# ---------------------------------------------------------------------------
# 4. test_autodetect_encoding_chardet_string
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_autodetect_encoding_chardet_string():
    """autodetect_encoding='chardet' (a string, not a bool) triggers charset
    auto-detection via the chardet library."""
    chardet = pytest.importorskip("chardet")
    las = las_rs.read(
        os.path.join(ENCODINGS_DIR, "utf8.las"),
        autodetect_encoding="chardet",
    )
    assert isinstance(las, las_rs.LASFile)
    assert len(las.curves) > 0


# ---------------------------------------------------------------------------
# 5. test_autodetect_encoding_chars_zero
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_autodetect_encoding_chars_zero():
    """autodetect_encoding_chars=0 reads zero bytes for sniffing but the file
    is still loaded (falls back to a default encoding)."""
    las = las_rs.read(
        os.path.join(ENCODINGS_DIR, "utf8.las"),
        autodetect_encoding_chars=0,
    )
    assert isinstance(las, las_rs.LASFile)
    dept = las.curves["DEPT"].data
    assert len(dept) == 3


# ---------------------------------------------------------------------------
# 6. test_encoding_errors_strict
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_encoding_errors_strict():
    """encoding_errors='strict' causes a UnicodeDecodeError when the file
    contains bytes that are invalid in the chosen encoding (UTF-8)."""
    with pytest.raises((UnicodeDecodeError, las_rs.LASUnknownUnitError, Exception)):
        las_rs.read(_LATIN1_BAD_FILE, encoding="utf-8", encoding_errors="strict")


# ---------------------------------------------------------------------------
# 7. test_encoding_errors_ignore
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_encoding_errors_ignore():
    """encoding_errors='ignore' silently drops bytes that are invalid in the
    chosen encoding; the file still loads and has the expected number of curves."""
    las = las_rs.read(
        _LATIN1_BAD_FILE,
        encoding="utf-8",
        encoding_errors="ignore",
    )
    assert isinstance(las, las_rs.LASFile)
    # The structural parts of the file are valid UTF-8, so all 3 data rows
    # and 2 curves must be present after bad bytes are dropped.
    assert len(las.curves) == 2
    dept = las.curves["DEPT"].data
    assert len(dept) == 3
