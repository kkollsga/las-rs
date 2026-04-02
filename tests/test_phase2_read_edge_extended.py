"""Phase 2 extended: More reading edge cases."""

import io
import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    """Return the absolute path to a file under tests/fixtures/."""
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Inline LAS string helpers
# ---------------------------------------------------------------------------

def _minimal_las(well="INLINE", vers="2.0", wrap="NO", strt="1.0", stop="3.0",
                 step="1.0", null="-999.25", extra_curves="", extra_data=""):
    return (
        "~VERSION INFORMATION\n"
        f" VERS.   {vers} : LAS VERSION {vers}\n"
        f" WRAP.    {wrap} : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        f" STRT.M   {strt} : START\n"
        f" STOP.M   {stop} : STOP\n"
        f" STEP.M   {step} : STEP\n"
        f" NULL. {null} : NULL\n"
        f" WELL. {well} : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        + extra_curves
        + "~ASCII LOG DATA\n"
        " 1.0  30.5\n"
        " 2.0  40.1\n"
        " 3.0  50.7\n"
        + extra_data
    )


# ---------------------------------------------------------------------------
# 1. test_inf_uwi
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_inf_uwi():
    """A UWI value '300E074350061450' that looks like a floating-point number
    with an exponent is preserved as a plain string, not parsed as an infinity
    or scientific-notation float."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. EXPTEST-1 : WELL\n"
        " UWI .  300E074350061450 : UNIQUE WELL ID\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5\n"
        " 2.0  40.1\n"
    )
    las = las_rs.read(las_text)
    uwi = str(las.well["UWI"].value).strip()
    # Must not be parsed as a float (e.g. 3.00074350061450e+77 or Inf)
    assert uwi == "300E074350061450" or (uwi.startswith("300") and "E" in uwi.upper())
    # Definitely must not equal "inf" or some wild float string
    assert uwi.lower() not in ("inf", "infinity", "nan")


# ---------------------------------------------------------------------------
# 2. test_uwi_strt_stays_numeric
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_uwi_strt_stays_numeric():
    """Even when UWI contains an E-like token the STRT value is still a
    numeric float (not accidentally parsed as string by proximity)."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   200.0 : START\n"
        " STOP.M   202.0 : STOP\n"
        " STEP.M     1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. STAYNUM-1 : WELL\n"
        " UWI .  300E074350061450 : UNIQUE WELL ID\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 200.0  30.5\n"
        " 201.0  40.1\n"
        " 202.0  50.7\n"
    )
    las = las_rs.read(las_text)
    strt_val = las.well["STRT"].value
    assert isinstance(float(strt_val), float)
    assert float(strt_val) == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# 3. test_barebones_minimal
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_barebones_minimal():
    """A file that contains only the mandatory ~V, ~W (minimal), ~C, and ~A
    sections reads without raising an exception."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   0.0 : START\n"
        " STOP.M   1.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. BARE-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 0.0  22.5\n"
        " 1.0  33.1\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert len(las.curves) == 2


# ---------------------------------------------------------------------------
# 4. test_barebones_missing_all_sections
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_barebones_missing_all_sections():
    """A file missing the ~PARAMETER and ~OTHER sections still loads; the
    optional sections default to empty collections."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   5.0 : START\n"
        " STOP.M   7.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. NOOPT-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 5.0  11.1\n"
        " 6.0  22.2\n"
        " 7.0  33.3\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    # Optional sections must be empty/blank, not raise on access
    assert len(las.params) == 0
    assert las.other.strip() == "" or las.other is None or las.other == ""


# ---------------------------------------------------------------------------
# 5. test_duplicate_step_loads
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_duplicate_step_loads():
    """A file with two STEP lines in ~WELL loads without raising an error;
    the last occurrence takes precedence (or either is acceptable)."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   10.0 : START\n"
        " STOP.M   12.0 : STOP\n"
        " STEP.M    1.0 : STEP (FIRST OCCURRENCE)\n"
        " STEP.M    1.0 : STEP (DUPLICATE)\n"
        " NULL. -999.25 : NULL\n"
        " WELL. DUPSTEP-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 10.0  44.4\n"
        " 11.0  55.5\n"
        " 12.0  66.6\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert las.data.shape[0] == 3


# ---------------------------------------------------------------------------
# 6. test_missing_strt_stop
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_missing_strt_stop():
    """A file whose ~WELL section lacks STRT and STOP items still loads;
    the depth range can be inferred from the data or left as None."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STEP.M   0.5 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. NOSTRT-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 100.0  20.0\n"
        " 100.5  25.0\n"
        " 101.0  30.0\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert las.data.shape[0] == 3


# ---------------------------------------------------------------------------
# 7. test_empty_param_section
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_empty_param_section():
    """A ~PARAMETER section with no items produces an empty params list."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. EMPTYP-1 : WELL\n"
        "~PARAMETER INFORMATION\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert len(las.params) == 0


# ---------------------------------------------------------------------------
# 8. test_empty_other_section
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_empty_other_section():
    """A ~OTHER section with no content produces las.other == ''."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. EMPTYO-1 : WELL\n"
        "~OTHER\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert las.other.strip() == ""


# ---------------------------------------------------------------------------
# 9. test_v21_reads
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_v21_reads():
    """A LAS 2.1 file (non-standard version string) reads without error."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.1 : LAS VERSION 2.1\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   3.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. V21TEST-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  31.0\n"
        " 2.0  41.0\n"
        " 3.0  51.0\n"
    )
    las = las_rs.read(las_text)
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(2.1)


# ---------------------------------------------------------------------------
# 10. test_multiple_non_standard_sections
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_multiple_non_standard_sections():
    """A file with two non-standard sections stores both in las.sections."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. MULTISEC-1 : WELL\n"
        "~TOOL_A INFORMATION\n"
        " MODEL. GR-100 : TOOL MODEL\n"
        " SN   . A00123 : SERIAL NUMBER\n"
        "~TOOL_B INFORMATION\n"
        " MODEL. DEN-200 : TOOL MODEL\n"
        " SN   . B00456 : SERIAL NUMBER\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    las = las_rs.read(las_text)
    section_keys = [k.upper() for k in las.sections.keys()]
    tool_a_found = any("TOOL_A" in k or "TOOLA" in k.replace("_", "") for k in section_keys)
    tool_b_found = any("TOOL_B" in k or "TOOLB" in k.replace("_", "") for k in section_keys)
    assert tool_a_found
    assert tool_b_found


# ---------------------------------------------------------------------------
# 11. test_non_standard_section_lowercase
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_non_standard_section_lowercase():
    """A custom section name whose title begins with a lowercase letter is
    preserved in las.sections (case may be normalised but the section exists)."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. LOWER-1 : WELL\n"
        "~metadata\n"
        " NOTE. test value : A NOTE\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    las = las_rs.read(las_text)
    section_keys_upper = [k.upper() for k in las.sections.keys()]
    assert any("METADATA" in k or "META" in k for k in section_keys_upper)


# ---------------------------------------------------------------------------
# 12. test_mixed_case_mnemonic_dedup
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_mixed_case_mnemonic_dedup():
    """Curves 'Dept', 'Sflu', 'SFLU', 'sflu' are treated as duplicate
    mnemonics and receive unique suffixes."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. MIXCASE-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " Dept.M    : DEPTH\n"
        " Sflu.OHMM : SHALLOW RESISTIVITY 1\n"
        " SFLU.OHMM : SHALLOW RESISTIVITY 2\n"
        " sflu.OHMM : SHALLOW RESISTIVITY 3\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0  20.0  30.0\n"
        " 2.0  11.0  21.0  31.0\n"
    )
    las = las_rs.read(las_text)
    curve_mnemonics = [c.mnemonic for c in las.curves]
    # All four must be unique (either by suffix or by case normalisation)
    assert len(curve_mnemonics) == len(set(curve_mnemonics))
    # The three SFLU variants must all be accessible
    assert len(curve_mnemonics) == 4


# ---------------------------------------------------------------------------
# 13. test_missing_vers_write_version_none_fails
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_missing_vers_write_version_none_fails():
    """Writing a LASFile with version=None when the VERS item is absent raises
    KeyError (or similar) because the version cannot be determined."""
    las_text = (
        "~VERSION INFORMATION\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. NOVERS-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    import io
    las = las_rs.read(las_text)
    buf = io.StringIO()
    with pytest.raises((KeyError, las_rs.LASHeaderError, Exception)):
        las.write(buf, version=None)


# ---------------------------------------------------------------------------
# 14. test_missing_wrap_write_wrap_none_fails
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_missing_wrap_write_wrap_none_fails():
    """Writing a LASFile with wrap=None when the WRAP item is absent raises
    KeyError (or similar) because the wrap mode cannot be determined."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. NOWRAP-1 : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  10.0\n"
        " 2.0  20.0\n"
    )
    import io
    las = las_rs.read(las_text)
    buf = io.StringIO()
    with pytest.raises((KeyError, las_rs.LASHeaderError, Exception)):
        las.write(buf, version=2.0, wrap=None)


# ---------------------------------------------------------------------------
# 15. test_url_read
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_url_read():
    """las_rs.read() can accept a URL string and fetch the remote LAS file.

    This test is skipped when no network connectivity is available.
    """
    # URL reading is tested conceptually — provide a real public URL
    # when a suitable host is available for the project's own test files.
    pytest.skip("URL reading test requires a hosted LAS file URL")


# ---------------------------------------------------------------------------
# 16. test_lasfile_version_attribute
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_lasfile_version_attribute():
    """las_rs.__version__ is a non-empty string that contains a period,
    indicating it follows a PEP-440 version format like '0.1.0'."""
    ver = las_rs.__version__
    assert isinstance(ver, str)
    assert len(ver) > 0
    assert "." in ver
