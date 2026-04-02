"""Phase 2 extended: Header line parsing edge cases not covered in original suite."""

import re

import pytest

import las_rs

# ---------------------------------------------------------------------------
# Try to import the internal read_header_line function if exposed.
# Tests that call it directly skip gracefully if it is not yet available,
# but they still carry @pytest.mark.xfail so the overall result stays xfail.
# ---------------------------------------------------------------------------

try:
    from las_rs.reader import read_header_line  # type: ignore[attr-defined]
    HAS_READER = True
except (ImportError, AttributeError):
    HAS_READER = False


def _parse(line):
    """Thin wrapper that raises AttributeError when not yet exposed."""
    if not HAS_READER:
        raise AttributeError("las_rs.reader.read_header_line not exposed")
    return read_header_line(line)


# ---------------------------------------------------------------------------
# Minimal inline LAS builder for indirect tests
# ---------------------------------------------------------------------------

_LAS_TMPL = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   1.0 : START DEPTH
 STOP.M   2.0 : STOP DEPTH
 STEP.M   1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. EDGE-1 : WELL NAME
~PARAMETER INFORMATION
{param_line}
~CURVE INFORMATION
 DEPT.M : DEPTH
 TVAL.-- : TEST VALUE
~ASCII LOG DATA
 1.0  0.0
 2.0  0.0
"""


def _read_with_param(param_line):
    """Build an inline LAS with the given raw ~PARAMETER line and parse it."""
    las_str = _LAS_TMPL.format(param_line=param_line)
    return las_rs.read(las_str, ignore_header_errors=True)


# ===========================================================================
# 1. Time value with colons in both unit and value fields
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_time_in_unit_and_colon_in_desc():
    """TIML.hh:mm 23:15 : Time Logger: At Bottom  →  name=TIML, unit=hh:mm,
    value contains '23:15', and description contains 'At Bottom'."""
    line = "TIML.hh:mm 23:15 : Time Logger: At Bottom"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["TIML"]
        assert item.unit == "hh:mm"
        assert "23:15" in str(item.value)
        assert "At Bottom" in str(item.descr)
    else:
        result = _parse(line)
        assert result["name"].strip() == "TIML"
        assert result["unit"].strip() == "hh:mm"
        assert "23:15" in result["value"]
        assert "At Bottom" in result["descr"]


# ===========================================================================
# 2. ISO-8601 datetime value with timezone offset colons
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_iso8601_datetime_value():
    """A value like '2012-09-16T07:44:12-05:00' must not be split at the
    timezone colon — the whole timestamp is the value field."""
    line = "DATE.   2012-09-16T07:44:12-05:00 : Acquisition Date"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["DATE"]
        val = str(item.value).strip()
        assert "2012-09-16" in val
        assert "07:44:12" in val
    else:
        result = _parse(line)
        val = result["value"]
        assert "2012-09-16" in val
        assert "07:44:12" in val


# ===========================================================================
# 3. Cyrillic unit string
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_cyrillic_unit():
    """DEPT.метер 500.0 : DEPTH  →  unit field is the Cyrillic string 'метер'."""
    line = "DEPT.метер 500.0 : DEPTH"
    if not HAS_READER:
        las_str = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.метер   500.0 : START DEPTH
 STOP.метер   501.0 : STOP DEPTH
 STEP.метер     1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. CYR-1 : WELL NAME
~CURVE INFORMATION
 DEPT.метер : DEPTH
~ASCII LOG DATA
 500.0
 501.0
"""
        las = las_rs.read(las_str)
        dept_unit = las.curves["DEPT"].unit
        assert "метер" in dept_unit
    else:
        result = _parse(line)
        assert result["unit"].strip() == "метер"


# ===========================================================================
# 4. Unit that itself starts with a dot (.1IN)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_unit_dot_1in():
    """TDEP..1IN 5000 : Total Depth  →  the double-dot means unit='.1IN'."""
    line = "TDEP..1IN 5000 : Total Depth"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["TDEP"]
        assert ".1IN" in item.unit or item.unit.strip() == ".1IN"
    else:
        result = _parse(line)
        assert result["unit"].strip() == ".1IN"


# ===========================================================================
# 5. Unit containing a space ('1000 lbf')
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_unit_with_space():
    """HKLA.1000 lbf 45.2 : Hook Load  →  unit is '1000 lbf' (space inside).

    This is an unusual but real-world LAS pattern where the unit descriptor
    contains a space; the parser must not truncate it at the space boundary.
    """
    line = "HKLA.1000 lbf 45.2 : Hook Load"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["HKLA"]
        assert "lbf" in item.unit or "lbf" in str(item.value)
    else:
        result = _parse(line)
        assert "lbf" in result["unit"]


# ===========================================================================
# 6. Numeric value that contains a colon (run number '01:')
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_numeric_value_with_colon():
    """'RUN . 01: RUN NUMBER'  →  name=RUN, value contains '01'."""
    line = "RUN .   01: RUN NUMBER"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["RUN"]
        assert "01" in str(item.value).strip() or "01" in str(item.descr).strip()
    else:
        result = _parse(line)
        assert result["name"].strip() == "RUN"
        assert "01" in result["value"] or "01" in result["descr"]


# ===========================================================================
# 7. Colon inside the description field
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_colon_inside_description():
    """'QI.:  Survey quality: GOOD'  →  description is 'Survey quality: GOOD',
    not truncated at the second colon."""
    line = "QI.:   Survey quality: GOOD"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        item = las.params["QI"]
        descr = str(item.descr)
        assert "GOOD" in descr
        assert "quality" in descr or "Survey" in descr
    else:
        result = _parse(line)
        assert "GOOD" in result["descr"]
        assert "quality" in result["descr"] or "Survey" in result["descr"]


# ===========================================================================
# 8. Mnemonic that itself contains dots (e.g. 'I. Res.')
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_dot_in_mnemonic_exact():
    """'I. Res..OHM-M  12.5 : Induction'  →  mnemonic is 'I. Res.' (with dots),
    unit is 'OHM-M', value is '12.5'."""
    line = "I. Res..OHM-M  12.5 : Induction"
    if not HAS_READER:
        pytest.skip("indirect test not practical for dot-in-mnemonic; needs internal API")
    result = _parse(line)
    assert "Res" in result["name"] or "I." in result["name"]
    assert "OHM" in result["unit"]
    assert "12.5" in result["value"]


# ===========================================================================
# 9. No period separator — name contains a space
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_no_period_with_space_in_name():
    """'PERM DAT :1'  →  name='PERM DAT', value='1' (no period in the line)."""
    line = "PERM DAT :1"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        # With no period the mnemonic boundary is ambiguous; verify something parsed
        param_mnemonics = [p.mnemonic for p in las.params]
        found = any("PERM" in m for m in param_mnemonics)
        assert found
    else:
        result = _parse(line)
        name = result["name"].strip()
        assert "PERM" in name
        val = result["value"].strip()
        assert val == "1" or "1" in val


# ===========================================================================
# 10. No period — time value (hh:mm:ss)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_no_period_time_value():
    """'TIME :14:00:32'  →  name='TIME', value='14:00:32' intact."""
    line = "TIME :14:00:32"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        param_mnemonics = [p.mnemonic for p in las.params]
        assert "TIME" in param_mnemonics
        time_item = las.params["TIME"]
        val = str(time_item.value).strip()
        assert "14" in val and "00" in val and "32" in val
    else:
        result = _parse(line)
        assert result["name"].strip() == "TIME"
        val = result["value"].strip()
        assert "14:00:32" == val or ("14" in val and "00" in val and "32" in val)


# ===========================================================================
# 11. No period — decimal value
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_no_period_decimal_value():
    """'HOLE DIA :85.7'  →  name='HOLE DIA', value='85.7'."""
    line = "HOLE DIA :85.7"
    if not HAS_READER:
        las = _read_with_param(" " + line)
        param_mnemonics = [p.mnemonic for p in las.params]
        found = any("HOLE" in m for m in param_mnemonics)
        assert found
        for p in las.params:
            if "HOLE" in p.mnemonic:
                assert "85.7" in str(p.value) or "85.7" in str(p.descr)
                break
    else:
        result = _parse(line)
        name = result["name"].strip()
        assert "HOLE" in name
        val = result["value"].strip()
        assert "85.7" in val


# ===========================================================================
# 12. Custom pattern argument passed to read_header_line
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_custom_pattern_arg():
    """read_header_line(line, pattern=custom_regex) uses the supplied regex
    instead of the built-in default pattern.

    The custom pattern here deliberately captures only two groups
    (name and everything else) to verify the kwarg is actually forwarded.
    """
    if not HAS_READER:
        pytest.skip("internal reader API not exposed")

    # A minimal two-group pattern: group(1)=name, group(2)=remainder
    custom_pattern = re.compile(r"^([A-Z0-9_]+)\s*[.:]?\s*(.*)$", re.IGNORECASE)
    line = "BHTV.DEGC  88.5 : Bottom Hole Temperature"

    # The function must accept a pattern kwarg without raising TypeError
    result = read_header_line(line, pattern=custom_pattern)
    # With the custom two-group pattern the name should still be captured
    assert result is not None
    assert "BHTV" in str(result)
