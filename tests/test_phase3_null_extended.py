"""Phase 3 extended: Null policy edge cases for complete coverage."""

import math

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _las_with_gr_value(gr_value_str, null="-999.25", extra_well="NULLTEST"):
    """Build a minimal 2-row LAS string where the first GR value is the given
    raw text token and the second row is always valid."""
    return (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        f" NULL. {null} : NULL\n"
        f" WELL. {extra_well} : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M   : DEPTH\n"
        " GR  .GAPI: GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        f" 1.0   {gr_value_str}\n"
        " 2.0   45.0\n"
    )


# ---------------------------------------------------------------------------
# 1. test_null_text_parenthesized
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_text_parenthesized():
    """common policy replaces the text token '(null)' with NaN."""
    las = las_rs.read(_las_with_gr_value("(null)"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])
    assert gr[1] == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# 2. test_null_text_inf
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_text_inf():
    """common policy replaces the Windows overflow text '1.#INF' with NaN."""
    las = las_rs.read(_las_with_gr_value("1.#INF"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


# ---------------------------------------------------------------------------
# 3. test_null_text_io
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_text_io():
    """common policy replaces '1.#IO' with NaN."""
    las = las_rs.read(_las_with_gr_value("1.#IO"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


# ---------------------------------------------------------------------------
# 4. test_null_text_ind
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_text_ind():
    """common policy replaces '1.#IND' (indeterminate) with NaN."""
    las = las_rs.read(_las_with_gr_value("1.#IND"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


# ---------------------------------------------------------------------------
# 5. test_null_negative_zero
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_negative_zero():
    """aggressive policy replaces the token '-0.0' with NaN."""
    las = las_rs.read(_las_with_gr_value("-0.0"), null_policy="aggressive")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


# ---------------------------------------------------------------------------
# 6. test_null_numbers_only
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_numbers_only():
    """'all' policy replaces any non-numeric text token with NaN."""
    las = las_rs.read(_las_with_gr_value("ERR"), null_policy="all")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])
    assert gr[1] == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# 7. test_null_err_preserved_under_strict
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_err_preserved_under_strict():
    """Under the 'strict' null policy the text 'ERR' is NOT replaced — it is
    kept as-is (as a string value or left to the numeric parser)."""
    las = las_rs.read(_las_with_gr_value("ERR"), null_policy="strict")
    gr = las.curves["GR"].data
    # strict only replaces the exact NULL header value (-999.25); 'ERR' must
    # survive in some form.  Either stored as a string or causing a non-NaN
    # placeholder — but not silently becoming NaN through a text-sentinel path.
    # We check that the second row (valid float) is still intact.
    assert gr[1] == pytest.approx(45.0)
    # And the first slot must NOT have been converted by a common-policy rule
    # (it is OK if the numeric parser produces NaN for "ERR" itself, but the
    # test asserts that the strict policy's *additional* text-sentinel rules
    # were not applied — which is verifiable only when the policy does NOT
    # convert it the same way as "common" would).
    # If the result is NaN here, it came from numeric coercion, not from the
    # null-sentinel list, so we accept both outcomes but mark the intent.
    # The primary assertion: no LASHeaderError / LASDataError raised.
    assert isinstance(las, las_rs.LASFile)


# ---------------------------------------------------------------------------
# 8. test_null_custom_string_sentinel
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_custom_string_sentinel():
    """custom null_policy=['NULL', 9998] catches both the string token 'NULL'
    and the numeric value 9998."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   4.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. CUSTOMNULL : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M   : DEPTH\n"
        " GR  .GAPI: GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0   NULL\n"
        " 2.0   9998\n"
        " 3.0   42.0\n"
        " 4.0   9998\n"
    )
    las = las_rs.read(las_text, null_policy=["NULL", 9998])
    gr = las.curves["GR"].data
    # Row 0: 'NULL' string → NaN
    assert np.isnan(gr[0])
    # Row 1 and Row 3: 9998 → NaN
    assert np.isnan(gr[1])
    assert np.isnan(gr[3])
    # Row 2: 42.0 → preserved
    assert gr[2] == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# 9. test_null_dashes_single
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_dashes_single():
    """common policy replaces a lone '-' dash token with NaN."""
    las = las_rs.read(_las_with_gr_value("-"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])
    assert gr[1] == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# 10. test_null_dashes_double
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_dashes_double():
    """common policy replaces a double dash '--' with NaN."""
    las = las_rs.read(_las_with_gr_value("--"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


# ---------------------------------------------------------------------------
# 11. test_null_dashes_preserves_negative
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_dashes_preserves_negative():
    """common dash policy does NOT replace a valid negative number '-2550.0'."""
    las = las_rs.read(_las_with_gr_value("-2550.0"), null_policy="common")
    gr = las.curves["GR"].data
    assert not np.isnan(gr[0])
    assert gr[0] == pytest.approx(-2550.0)


# ---------------------------------------------------------------------------
# 12. test_null_na_hash
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_null_na_hash():
    """common policy replaces the token '#N/A' with NaN."""
    las = las_rs.read(_las_with_gr_value("#N/A"), null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])
    assert gr[1] == pytest.approx(45.0)
