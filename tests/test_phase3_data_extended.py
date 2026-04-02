"""Phase 3 extended: Data section parsing edge cases."""

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_inline(las_text, **kwargs):
    return las_rs.read(las_text, **kwargs)


def _minimal_header(well="INLINE-TEST", null="-999.25"):
    return (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : ONE LINE PER DEPTH STEP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   3.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        f" NULL. {null} : NULL\n"
        f" WELL. {well} : WELL\n"
    )


# ---------------------------------------------------------------------------
# 1. test_quoted_strings_in_data
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_quoted_strings_in_data():
    """A quoted string containing a space in the data section is treated as one
    token, not split on the whitespace."""
    las_text = (
        _minimal_header("QUOTEDTEST")
        + "~CURVE INFORMATION\n"
        " DEPT.M        : DEPTH\n"
        " LITH.         : LITHOLOGY\n"
        "~ASCII LOG DATA\n"
        ' 1.0  "pick gamma"\n'
        ' 2.0  sandstone\n'
        ' 3.0  shale\n'
    )
    las = _read_inline(las_text)
    lith = las.curves["LITH"].data
    # The quoted token must survive as a single value, not two tokens
    assert "pick gamma" in str(lith[0]) or "pick" in str(lith[0])


# ---------------------------------------------------------------------------
# 2. test_chr26_removal
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_chr26_removal():
    """chr(26) (Ctrl-Z, the DOS EOF marker) embedded in the data section is
    silently stripped and does not corrupt parsing."""
    las_text = (
        _minimal_header("CHR26TEST")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5\n"
        " 2.0  40.1\x1a\n"  # chr(26) embedded after value
        " 3.0  50.7\n"
    )
    las = _read_inline(las_text)
    gr = las.curves["GR"].data
    assert len(gr) == 3
    assert gr[1] == pytest.approx(40.1)


# ---------------------------------------------------------------------------
# 3. test_reshape_error_raises
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_reshape_error_raises():
    """Data that cannot reshape into n_columns raises LASDataError, not a
    generic ValueError."""
    las_text = (
        _minimal_header("RESHAPEERR")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        " RHOB.G/CC : DENSITY\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5\n"        # only 2 columns instead of 3
        " 2.0  40.1\n"
        " 3.0  50.7\n"
    )
    with pytest.raises(las_rs.LASDataError):
        _read_inline(las_text)


# ---------------------------------------------------------------------------
# 4. test_comma_decimal_in_params
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_comma_decimal_in_params():
    """Comma-decimal substitution also applies to parameter section values so
    that '72,5' in a ~PARAMETER section is read as the float 72.5."""
    las_text = (
        _minimal_header("COMMAPARAMS")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        "~PARAMETER INFORMATION\n"
        " BHT .DEGC  72,5 : BOTTOM HOLE TEMPERATURE\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5\n"
        " 2.0  40.1\n"
        " 3.0  50.7\n"
    )
    las = _read_inline(las_text, read_policy="comma-decimal-mark")
    bht_val = las.params["BHT"].value
    assert float(str(bht_val).replace(",", ".")) == pytest.approx(72.5)


# ---------------------------------------------------------------------------
# 5. test_string_data_time_column
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_string_data_time_column():
    """A TIME column containing HH:MM:SS strings is preserved as string data,
    not coerced to NaN."""
    las_text = (
        _minimal_header("TIMETEST")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " TIME.     : TIME OF MEASUREMENT\n"
        "~ASCII LOG DATA\n"
        " 1.0  00:00:00\n"
        " 2.0  00:01:00\n"
        " 3.0  00:02:00\n"
    )
    las = _read_inline(las_text)
    time_data = las.curves["TIME"].data
    # Values must be strings (or object dtype), not NaN
    assert len(time_data) == 3
    non_nan = [v for v in time_data if str(v) not in ("nan", "")]
    assert len(non_nan) == 3
    assert "00:00:00" in str(time_data[0])


# ---------------------------------------------------------------------------
# 6. test_string_data_date_column
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_string_data_date_column():
    """A DATE column containing 'DD-Mon-YY' strings is preserved as string data."""
    las_text = (
        _minimal_header("DATETEST")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " DATE.     : DATE OF MEASUREMENT\n"
        "~ASCII LOG DATA\n"
        " 1.0  01-Jan-20\n"
        " 2.0  02-Jan-20\n"
        " 3.0  03-Jan-20\n"
    )
    las = _read_inline(las_text)
    date_data = las.curves["DATE"].data
    assert len(date_data) == 3
    non_nan = [v for v in date_data if str(v) not in ("nan", "")]
    assert len(non_nan) == 3
    assert "Jan" in str(date_data[0])


# ---------------------------------------------------------------------------
# 7. test_numeric_looking_date
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_numeric_looking_date():
    """'2020-01-01' in a string column stays as a string, not evaluated as
    arithmetic (2020 minus 1 minus 1)."""
    las_text = (
        _minimal_header("ISODATE")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " DATE.     : ISO DATE\n"
        "~ASCII LOG DATA\n"
        " 1.0  2020-01-01\n"
        " 2.0  2020-01-02\n"
        " 3.0  2020-01-03\n"
    )
    las = _read_inline(las_text)
    date_data = las.curves["DATE"].data
    # Must not be parsed as the float 2018.0 (2020 - 1 - 1)
    first = str(date_data[0])
    assert first not in ("2018.0", "2018", "nan")
    assert "2020" in first or "01" in first


# ---------------------------------------------------------------------------
# 8. test_data_characters_pandas_dtypes
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_data_characters_pandas_dtypes():
    """After reading a LAS file with string and float columns, df() returns
    a DataFrame where string columns have dtype=object and float columns have
    dtype=float64."""
    pandas = pytest.importorskip("pandas")
    las_text = (
        _minimal_header("DTYPETEST")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        " LITH.     : LITHOLOGY\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5  sandstone\n"
        " 2.0  45.2  shale\n"
        " 3.0  60.8  limestone\n"
    )
    las = _read_inline(las_text)
    df = las.df()
    # The numeric GR column should be float64
    assert df["GR"].dtype == np.float64 or np.issubdtype(df["GR"].dtype, np.floating)
    # The string LITH column should be object dtype
    assert df["LITH"].dtype == object
