"""Phase 2 extended: All LASFile.read() keyword arguments coverage."""

import os
from io import StringIO

import numpy as np
import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Shared inline LAS strings
# ---------------------------------------------------------------------------

# Standard 2-curve, 3-row file used by most kwarg tests.
_LAS_BASIC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   200.0 : START DEPTH
 STOP.M   202.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  IRONCLAD PETROLEUM : COMPANY
 WELL.  FALCON-3 #1        : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 200.0   44.10
 201.0   67.30
 202.0   52.80
"""

# File with a malformed parameter line to test ignore_header_errors.
_LAS_DODGY_HEADER = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   10.0 : START DEPTH
 STOP.M   11.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. ERR-WELL : WELL NAME
~PARAMETER INFORMATION
!!!INVALID_PARAMETER_LINE_NO_DELIMITERS!!!
 BHT .DEGC  95.0 : Bottom Hole Temperature
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 10.0   55.0
 11.0   60.0
"""

# File with comment lines in the data section.
_LAS_DATA_COMMENTS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   300.0 : START DEPTH
 STOP.M   302.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 WELL. COMMENT-WELL : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
# This line is a data-section comment
 300.0   30.0
# Another comment between data rows
 301.0   35.0
 302.0   40.0
"""

# File with quote-prefixed "comment" lines to test custom ignore_comments.
_LAS_QUOTE_COMMENTS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   400.0 : START DEPTH
 STOP.M   401.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 WELL. QCMT-WELL : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
" This line starts with a double-quote and should be ignored
 400.0   22.0
 401.0   25.0
"""

# File with comma-separated decimal data (read_policy test).
_LAS_COMMA_DECIMAL = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   1671.0 : START DEPTH
 STOP.M   1673.0 : STOP DEPTH
 STEP.M      1.0 : STEP VALUE
 NULL. -999,25   : NULL VALUE
 WELL. COMMA-1 : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 1671,000   45,0
 1672,000   50,5
 1673,000   55,2
"""

# Wrapped file inline string.
_LAS_WRAPPED = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.   YES : WRAPPED DATA
~WELL INFORMATION
 STRT.M  500.0 : START DEPTH
 STOP.M  501.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. WRAP-WELL : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
 DT  .US/M : SONIC
 RHOB.G/CC : DENSITY
 NPHI.V/V  : NEUTRON
 CALI.IN   : CALIPER
~ASCII LOG DATA
 500.0
  38.5   75.2   2.441   0.312   8.62
 501.0
  42.1   80.0   2.510   0.290   8.50
"""

# Minimal file with mnemonic in mixed case to test mnemonic_case kwarg.
_LAS_MIXEDCASE = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   50.0 : START DEPTH
 STOP.M   51.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. MIX-WELL : WELL NAME
~CURVE INFORMATION
 Dept.M    : Depth
 Gr  .GAPI : Gamma Ray
~ASCII LOG DATA
 50.0   80.0
 51.0   85.0
"""


# ===========================================================================
# 1 & 2 — ignore_data
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_data_true():
    """read(ignore_data=True) returns a LASFile with no data rows but with
    header items intact (COMP should still be present)."""
    las = las_rs.read(_LAS_BASIC, ignore_data=True)
    assert isinstance(las, las_rs.LASFile)
    # Data must be absent
    assert las.data.size == 0 or las.data.shape[0] == 0
    # Headers must still exist
    assert las.well["COMP"].value is not None
    assert len(las.curves) > 0


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_data_false():
    """read(ignore_data=False) is the default and must populate las.data."""
    las = las_rs.read(_LAS_BASIC, ignore_data=False)
    assert las.data.shape[0] == 3
    assert las.curves["GR"].data[0] == pytest.approx(44.10)


# ===========================================================================
# 3 & 4 — engine
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_engine_numpy():
    """engine='numpy' parses the file correctly and the curve data is a numpy
    array with the expected values."""
    las = las_rs.read(_LAS_BASIC, engine="numpy")
    gr = las.curves["GR"].data
    assert isinstance(gr, np.ndarray)
    assert gr[1] == pytest.approx(67.30)


@pytest.mark.xfail(reason="not yet implemented")
def test_engine_normal():
    """engine='normal' produces the same depth and GR values as engine='numpy'."""
    las_n = las_rs.read(_LAS_BASIC, engine="numpy")
    las_r = las_rs.read(_LAS_BASIC, engine="normal")
    np.testing.assert_array_almost_equal(
        las_n.curves["GR"].data,
        las_r.curves["GR"].data,
        decimal=4,
    )


# ===========================================================================
# 5 — use_normal_engine_for_wrapped
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_use_normal_engine_for_wrapped():
    """WRAP=YES file read with use_normal_engine_for_wrapped=True still parses
    the data correctly using the normal (non-numpy) engine."""
    las = las_rs.read(
        _LAS_WRAPPED,
        use_normal_engine_for_wrapped=True,
    )
    dept = las.curves["DEPT"].data
    assert dept[0] == pytest.approx(500.0)
    assert dept[1] == pytest.approx(501.0)


# ===========================================================================
# 6, 7, 8 — mnemonic_case
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_upper():
    """mnemonic_case='upper' forces all curve mnemonics to upper-case regardless
    of how they appear in the file."""
    las = las_rs.read(_LAS_MIXEDCASE, mnemonic_case="upper")
    for curve in las.curves:
        assert curve.mnemonic == curve.mnemonic.upper()


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_lower():
    """mnemonic_case='lower' forces all curve mnemonics to lower-case."""
    las = las_rs.read(_LAS_MIXEDCASE, mnemonic_case="lower")
    for curve in las.curves:
        assert curve.mnemonic == curve.mnemonic.lower()


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_preserve():
    """mnemonic_case='preserve' keeps the mixed-case mnemonics exactly as
    written in the file ('Dept', 'Gr')."""
    las = las_rs.read(_LAS_MIXEDCASE, mnemonic_case="preserve")
    mnemonics = [c.mnemonic for c in las.curves]
    assert "Dept" in mnemonics
    assert "Gr" in mnemonics


# ===========================================================================
# 9 & 10 — ignore_header_errors
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_header_errors_false():
    """By default (ignore_header_errors=False) a malformed header line raises
    las_rs.LASHeaderError."""
    with pytest.raises(las_rs.LASHeaderError):
        las_rs.read(_LAS_DODGY_HEADER)


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_header_errors_true():
    """With ignore_header_errors=True the malformed line is skipped silently
    and the valid BHT parameter is still present."""
    las = las_rs.read(_LAS_DODGY_HEADER, ignore_header_errors=True)
    param_mnemonics = [p.mnemonic for p in las.params]
    assert "BHT" in param_mnemonics


# ===========================================================================
# 11 & 12 — ignore_comments
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_comments_default():
    """Lines starting with '#' inside header or data sections are silently
    ignored by default; the data rows count is correct (3 rows, not 5)."""
    las = las_rs.read(_LAS_DATA_COMMENTS)
    assert las.data.shape[0] == 3
    assert las.curves["GR"].data[0] == pytest.approx(30.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_comments_custom():
    """ignore_comments=('#', '"') also treats lines starting with a
    double-quote as comments; the resulting data has exactly 2 rows."""
    las = las_rs.read(_LAS_QUOTE_COMMENTS, ignore_comments=("#", '"'))
    assert las.data.shape[0] == 2
    assert las.curves["GR"].data[0] == pytest.approx(22.0)


# ===========================================================================
# 13 & 14 — read_policy
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_policy_default():
    """Default read_policy applies comma-decimal substitution so '1671,000'
    is parsed as the float 1671.0."""
    las = las_rs.read(_LAS_COMMA_DECIMAL)
    dept = las.curves["DEPT"].data
    assert dept[0] == pytest.approx(1671.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_read_policy_empty():
    """read_policy=() disables all pre-processing substitutions; comma-decimal
    values cannot be parsed as floats and must be NaN (or raise, caught by
    xfail)."""
    las = las_rs.read(_LAS_COMMA_DECIMAL, read_policy=())
    dept = las.curves["DEPT"].data
    # Without substitution '1671,000' is not a valid float
    assert np.isnan(dept[0]) or dept[0] != pytest.approx(1671.0)


# ===========================================================================
# 15 & 16 — null_policy
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_null_policy_strict():
    """null_policy='strict' replaces only the exact NULL header value (-999.25)
    with NaN and leaves all other values untouched."""
    las_text = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  10.0 : START
 STOP.M  12.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
 WELL. STRICT-1 : WELL
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 10.0  -999.25
 11.0   9999.0
 12.0   42.15
"""
    las = las_rs.read(las_text, null_policy="strict")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])          # -999.25 replaced
    assert not np.isnan(gr[1])      # 9999 kept by strict policy
    assert gr[1] == pytest.approx(9999.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_null_policy_none():
    """null_policy='none' preserves the raw -999.25 value as a float; no NaN
    substitution is performed."""
    las_text = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  20.0 : START
 STOP.M  21.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
 WELL. NONE-1 : WELL
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 20.0  -999.25
 21.0   38.5
"""
    las = las_rs.read(las_text, null_policy="none")
    gr = las.curves["GR"].data
    assert not np.isnan(gr[0])
    assert gr[0] == pytest.approx(-999.25)


# ===========================================================================
# 17 — accept_regexp_sub_recommendations
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_accept_regexp_sub_recommendations_true():
    """accept_regexp_sub_recommendations=True enables automatic removal of
    problematic run-on hyphen substitutions when hyphens appear in data
    values (e.g. UWI numbers with dashes)."""
    las_text = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   1.0 : START
 STOP.M   2.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
 WELL. HYPH-1 : WELL
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 1.0  50-60
 2.0  65.0
"""
    las = las_rs.read(las_text, accept_regexp_sub_recommendations=True)
    # With recommendations accepted, hyphen subs are disabled so '50-60'
    # is treated differently than with run-on handling active.
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# 18 — index_unit
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_index_unit_override():
    """index_unit='m' forces the depth index to be interpreted as metres
    even if the DEPT unit in the file says something else."""
    las_text = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FT   100.0 : START
 STOP.FT   102.0 : STOP
 STEP.FT     1.0 : STEP
 NULL. -999.25 : NULL
 WELL. UNIT-WELL : WELL
~CURVE INFORMATION
 DEPT.FT   : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 100.0  30.0
 101.0  35.0
 102.0  40.0
"""
    las = las_rs.read(las_text, index_unit="m")
    # The index unit override must be reflected in the DEPT curve or well header
    dept_unit = las.curves["DEPT"].unit
    strt_unit = las.well["STRT"].unit
    assert dept_unit.lower() == "m" or strt_unit.lower() == "m"


# ===========================================================================
# 19 – 22 — dtypes
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_auto():
    """dtypes='auto' (the default) converts numeric columns to float arrays
    and leaves non-numeric columns as string/object arrays."""
    las = las_rs.read(_LAS_BASIC, dtypes="auto")
    dept = las.curves["DEPT"].data
    gr = las.curves["GR"].data
    assert dept.dtype.kind == "f"
    assert gr.dtype.kind == "f"


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_dict():
    """dtypes={'GR': int} converts the GR curve to an integer array while
    leaving DEPT as float."""
    las = las_rs.read(_LAS_BASIC, dtypes={"GR": int})
    dept = las.curves["DEPT"].data
    gr = las.curves["GR"].data
    assert dept.dtype.kind == "f"
    assert gr.dtype.kind == "i"
    assert gr[0] == 44


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_list():
    """dtypes=[float, float] converts both DEPT and GR to float dtype."""
    las = las_rs.read(_LAS_BASIC, dtypes=[float, float])
    for curve in las.curves:
        assert curve.data.dtype.kind == "f"


@pytest.mark.xfail(reason="not yet implemented")
def test_dtypes_false():
    """dtypes=False keeps all values as raw strings (object array); numeric
    conversion is not performed."""
    las = las_rs.read(_LAS_BASIC, dtypes=False)
    dept = las.curves["DEPT"].data
    # Values should be string-like, not float
    assert dept.dtype.kind in ("U", "S", "O")
    assert "200" in str(dept[0])


# ===========================================================================
# 23 & 24 — encoding / encoding_errors
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_encoding_explicit():
    """encoding='utf-8' reads a plain ASCII/UTF-8 file correctly."""
    las = las_rs.read(_LAS_BASIC, encoding="utf-8")
    assert isinstance(las, las_rs.LASFile)
    assert las.curves["GR"].data[0] == pytest.approx(44.10)


@pytest.mark.xfail(reason="not yet implemented")
def test_encoding_errors_replace():
    """encoding_errors='replace' (the default) does not raise on bytes that
    cannot be decoded; a replacement character is used instead."""
    # Read the Latin-1 fixture with UTF-8 + replace to exercise the code path.
    latin1_path = fixture("encodings", "latin1.las")
    las = las_rs.read(latin1_path, encoding="utf-8", encoding_errors="replace")
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# 25 & 26 — autodetect_encoding
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_autodetect_encoding_true():
    """autodetect_encoding=True causes las_rs to use chardet (if available)
    to guess the file encoding; the Latin-1 fixture must still load."""
    latin1_path = fixture("encodings", "latin1.las")
    las = las_rs.read(latin1_path, autodetect_encoding=True)
    assert isinstance(las, las_rs.LASFile)
    assert len(las.curves) > 0


@pytest.mark.xfail(reason="not yet implemented")
def test_autodetect_encoding_false():
    """autodetect_encoding=False disables charset sniffing; a plain UTF-8
    file must still parse correctly using the default encoding."""
    las = las_rs.read(_LAS_BASIC, autodetect_encoding=False)
    assert isinstance(las, las_rs.LASFile)
    assert las.curves["GR"].data[2] == pytest.approx(52.80)


# ===========================================================================
# 27 — ignore_data_comments
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_data_comments():
    """ignore_data_comments='#' causes lines starting with '#' inside the
    ~ASCII section to be discarded before numeric parsing; resulting data
    has exactly 3 rows (the comment lines do not become NaN rows)."""
    las = las_rs.read(_LAS_DATA_COMMENTS, ignore_data_comments="#")
    assert las.data.shape[0] == 3
    gr = las.curves["GR"].data
    assert gr[0] == pytest.approx(30.0)
    assert gr[1] == pytest.approx(35.0)
    assert gr[2] == pytest.approx(40.0)
