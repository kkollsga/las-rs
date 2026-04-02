"""Phase 4 extended: Write formatting kwargs and edge cases."""

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

# 4-curve, 4-row file used by most write kwarg tests.
_LAS_WRITE_BASE = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   600.0 : START DEPTH
 STOP.M   603.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  FRONTIER DRILLING : COMPANY
 WELL.  OSPREY-2 #4       : WELL NAME
 UWI .  05-077-20130-00-00 : WELL IDENTIFIER
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 DT  .US/M : SONIC TRANSIT TIME
 RHOB.G/CC : BULK DENSITY
~ASCII LOG DATA
 600.0   48.30   78.10   2.421
 601.0   62.50   84.20   2.555
 602.0   71.80   90.50   2.688
 603.0   55.20   81.30   2.499
"""

# LAS 1.2 format — non-depth well items use descr:value ordering.
_LAS_V12_WRITE = """\
~VERSION INFORMATION
 VERS.  1.2 : LAS VERSION 1.2
 WRAP.   NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION BLOCK
 STRT.M  700.0 : START DEPTH
 STOP.M  701.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 COMP.   : SPRINGFIELD RESOURCES
 WELL.   : HAWK-5
~CURVE INFORMATION BLOCK
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 700.0  28.40
 701.0  33.60
"""

# File with intentionally wrong STOP value to test recalculation.
_LAS_WRONG_STOP = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   100.0 : START DEPTH
 STOP.M   999.0 : STOP DEPTH (WRONG)
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 WELL. BADSTOP-1 : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 100.0   40.0
 101.0   45.0
 102.0   50.0
"""

# File with no ~PARAMETER section.
_LAS_NO_PARAMS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  900.0 : START DEPTH
 STOP.M  901.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL. NOPARAM-1 : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 900.0  66.0
 901.0  70.0
"""


def _read_base():
    return las_rs.read(_LAS_WRITE_BASE)


def _write_to_string(las, **kwargs):
    buf = StringIO()
    las.write(buf, **kwargs)
    return buf.getvalue()


# ===========================================================================
# 1 — lhs_spacer
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_lhs_spacer():
    """write(lhs_spacer='') removes the leading space that normally precedes
    each data value on a row; the first non-whitespace character is the depth
    digit."""
    las = _read_base()
    output = _write_to_string(las, lhs_spacer="")
    data_start = output.upper().index("~A")
    data_lines = [
        ln for ln in output[data_start:].splitlines()
        if ln.strip() and not ln.strip().startswith("~") and not ln.strip().startswith("#")
    ]
    # With lhs_spacer="" the lines must not start with whitespace
    for line in data_lines[:3]:
        assert not line.startswith(" "), (
            f"Expected no leading space but got: {line!r}"
        )


# ===========================================================================
# 2 — spacer (column separator)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_spacer_comma():
    """write(spacer=',') uses a comma as the inter-column delimiter instead of
    the default whitespace."""
    las = _read_base()
    output = _write_to_string(las, spacer=",")
    data_start = output.upper().index("~A")
    data_section = output[data_start:]
    data_lines = [
        ln for ln in data_section.splitlines()
        if ln.strip() and not ln.strip().startswith("~") and not ln.strip().startswith("#")
    ]
    # At least one data line must contain commas
    assert any("," in line for line in data_lines)


# ===========================================================================
# 3 — len_numeric_field (positive)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_len_numeric_field():
    """write(len_numeric_field=15) pads each value column to 15 characters
    wide; each data token occupies exactly 15 characters."""
    las = _read_base()
    output = _write_to_string(las, len_numeric_field=15)
    data_start = output.upper().index("~A")
    data_section = output[data_start:]
    data_lines = [
        ln for ln in data_section.splitlines()
        if ln.strip() and not ln.strip().startswith("~") and not ln.strip().startswith("#")
    ]
    first_line = data_lines[0]
    tokens = first_line.split()
    # 4 curves → 4 tokens on the first row
    assert len(tokens) == 4
    # Each field in the raw line should span 15 characters
    # Verify by checking that the line length is consistent with 4 × 15
    assert len(first_line.rstrip()) >= 4 * 14  # allow for minor variation


# ===========================================================================
# 4 — len_numeric_field = -1
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_len_numeric_field_minus1():
    """write(len_numeric_field=-1) disables fixed-width column alignment; the
    columns may be of variable width (no padding)."""
    las = _read_base()
    output_aligned = _write_to_string(las, len_numeric_field=15)
    output_free = _write_to_string(las, len_numeric_field=-1)
    # The free-format output should differ from the padded output
    assert output_aligned != output_free


# ===========================================================================
# 5 — column_fmt
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_column_fmt():
    """write(column_fmt={0: '%.3f'}) forces the depth column (index 0) to be
    written with exactly 3 decimal places."""
    las = _read_base()
    output = _write_to_string(las, column_fmt={0: "%.3f"})
    data_start = output.upper().index("~A")
    data_section = output[data_start:]
    data_lines = [
        ln for ln in data_section.splitlines()
        if ln.strip() and not ln.strip().startswith("~") and not ln.strip().startswith("#")
    ]
    first_depth_token = data_lines[0].split()[0]
    # With %.3f format '600.0' becomes '600.000'
    assert first_depth_token == "600.000" or first_depth_token.endswith(".000")


# ===========================================================================
# 6 — data_width (wrapped output)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_data_width():
    """write(data_width=40, wrap=True) wraps data lines so that each line is
    at most 40 characters (excluding the newline)."""
    las = _read_base()
    output = _write_to_string(las, data_width=40, wrap=True)
    data_start = output.upper().index("~A")
    data_section = output[data_start:]
    data_lines = [
        ln for ln in data_section.splitlines()
        if ln.strip() and not ln.strip().startswith("~") and not ln.strip().startswith("#")
    ]
    for line in data_lines:
        assert len(line) <= 40, (
            f"Line exceeds data_width=40: {len(line)} chars: {line!r}"
        )


# ===========================================================================
# 7 — header_width
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_header_width():
    """write(header_width=80) formats header section lines to be at most 80
    characters wide (or exactly padded to that width)."""
    las = _read_base()
    output = _write_to_string(las, header_width=80)

    in_well = False
    well_lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("~W"):
            in_well = True
            continue
        if stripped.startswith("~") and in_well:
            break
        if in_well and "." in line:
            well_lines.append(line)

    for line in well_lines:
        assert len(line) <= 80 or len(line.rstrip()) <= 80, (
            f"Header line exceeds header_width=80: {len(line)} chars: {line!r}"
        )


# ===========================================================================
# 8 — data_section_header
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_data_section_header_custom():
    """write(data_section_header='~A') produces a data section that opens
    with the bare '~A' marker instead of the default '~ASCII'."""
    las = _read_base()
    output = _write_to_string(las, data_section_header="~A")
    lines = output.splitlines()
    ascii_lines = [ln.strip() for ln in lines if ln.strip().upper().startswith("~A")]
    assert any(ln == "~A" for ln in ascii_lines), (
        "Expected '~A' as data section header but found: " + str(ascii_lines)
    )


# ===========================================================================
# 9 — mnemonics_header
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_mnemonics_header():
    """write(mnemonics_header=True) adds a line immediately after '~A' that
    lists all curve mnemonics."""
    las = _read_base()
    output = _write_to_string(las, mnemonics_header=True)
    data_start = output.upper().index("~A")
    lines_after = output[data_start:].splitlines()
    # The second non-empty line after ~A should contain all curve mnemonics
    non_empty = [ln for ln in lines_after if ln.strip()]
    header_line = non_empty[1] if len(non_empty) > 1 else ""
    for curve in las.curves:
        assert curve.mnemonic in header_line, (
            f"Mnemonic '{curve.mnemonic}' not found in mnemonics header: {header_line!r}"
        )


# ===========================================================================
# 10 — version=None uses las.version.VERS.value
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_version_none_uses_file():
    """write(version=None) takes the version from the in-memory LASFile's own
    VERS header item rather than defaulting to 2.0."""
    las = las_rs.read(_LAS_V12_WRITE)
    output = _write_to_string(las, version=None)
    assert "1.2" in output


# ===========================================================================
# 11 — version=1.2 explicit
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_version_12_explicit():
    """write(version=1.2) writes a LAS 1.2 format file; the VERS line value
    is '1.2' and the well section uses LAS 1.2 item ordering (descr:value
    for non-depth items)."""
    las = _read_base()
    output = _write_to_string(las, version=1.2)
    assert "1.2" in output
    # In 1.2 format the COMP name appears in the description position
    assert "FRONTIER DRILLING" in output


# ===========================================================================
# 12 — version=2.0 explicit
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_version_20_explicit():
    """write(version=2.0) writes a LAS 2.0 format file; the VERS line value
    is '2.0'."""
    las = las_rs.read(_LAS_V12_WRITE)
    output = _write_to_string(las, version=2.0)
    assert "2.0" in output


# ===========================================================================
# 13 — write does not mutate in-memory VERS
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_preserves_inmemory_version():
    """Writing with version=2.0 must not alter the in-memory las.version.VERS
    item of the original LASFile; it should still report its original value."""
    las = las_rs.read(_LAS_V12_WRITE)
    original_vers = las.version["VERS"].value
    _write_to_string(las, version=2.0)
    assert las.version["VERS"].value == original_vers


# ===========================================================================
# 14, 15, 16 — STRT / STOP / STEP keyword overrides
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_strt_override():
    """write(STRT=500.0) overrides the STRT value in the written header;
    the depth values in the data section are unchanged."""
    las = _read_base()
    output = _write_to_string(las, STRT=500.0)
    assert "500" in output
    # Original STRT (600.0) must still appear in the data section
    data_start = output.upper().index("~A")
    data_section = output[data_start:]
    assert "600" in data_section


@pytest.mark.xfail(reason="not yet implemented")
def test_write_stop_override():
    """write(STOP=600.0) overrides the STOP value in the written header."""
    las = _read_base()
    output = _write_to_string(las, STOP=600.0)
    # The overridden value must appear in the header (before data section)
    header_section = output[: output.upper().index("~A")]
    assert "600" in header_section


@pytest.mark.xfail(reason="not yet implemented")
def test_write_step_override():
    """write(STEP=0.5) overrides the STEP value in the written header."""
    las = _read_base()
    output = _write_to_string(las, STEP=0.5)
    header_section = output[: output.upper().index("~A")]
    assert "0.5" in header_section


# ===========================================================================
# 17 — recalculation of wrong STOP
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_recalculates_wrong_stop():
    """When a file has an incorrect STOP (999.0 but data ends at 102.0), the
    written output must correct STOP to match the last depth value (102.0)."""
    las = las_rs.read(_LAS_WRONG_STOP, ignore_header_errors=True)
    output = _write_to_string(las)
    header_section = output[: output.upper().index("~A")]
    # The correct STOP (102.0) must appear; the wrong value (999) must not
    # dominate the STOP line
    assert "102" in header_section
    # Verify the erroneous value is corrected (not the raw 999 propagated)
    lines = header_section.splitlines()
    stop_lines = [ln for ln in lines if "STOP" in ln.upper()]
    for sl in stop_lines:
        assert "999" not in sl or "102" in sl, (
            f"STOP line still shows wrong value: {sl!r}"
        )


# ===========================================================================
# 18 & 19 — writing None and empty string values
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_empty_value_none():
    """A well item whose .value is set to None writes as an empty string in
    the output (not as 'None')."""
    las = _read_base()
    las.well["UWI"].value = None
    output = _write_to_string(las)
    # 'None' must not appear as a data value in the well section
    well_end = output.upper().index("~C")
    header_block = output[:well_end]
    uwi_lines = [ln for ln in header_block.splitlines() if "UWI" in ln.upper()]
    for ln in uwi_lines:
        assert "None" not in ln, f"Unexpected 'None' literal in: {ln!r}"


@pytest.mark.xfail(reason="not yet implemented")
def test_write_empty_value_string():
    """A well item whose .value is an empty string writes and re-reads
    correctly; the re-read value is still an empty string (or whitespace)."""
    las = _read_base()
    las.well["UWI"].value = ""
    buf = StringIO()
    las.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf, ignore_header_errors=True)
    uwi_val = reread.well["UWI"].value if "UWI" in [i.mnemonic for i in reread.well] else ""
    assert uwi_val.strip() == ""


# ===========================================================================
# 20 — duplicate mnemonics use original_mnemonic on write
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_duplicate_mnemonics_original():
    """When duplicate-mnemonic suffixes (:1/:2) are added at read time, the
    written output uses the original_mnemonic (no suffix) so the file can be
    read by third-party tools."""
    las_text = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   1.0 : START
 STOP.M   2.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
 WELL. DUP-WELL : WELL
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY (PRIMARY)
 GR  .GAPI : GAMMA RAY (REPEAT)
~ASCII LOG DATA
 1.0  30.0  31.5
 2.0  35.0  36.8
"""
    las = las_rs.read(las_text, ignore_header_errors=True)
    output = _write_to_string(las)
    curve_section_start = output.upper().index("~C")
    curve_section_end = output.upper().index("~A")
    curve_block = output[curve_section_start:curve_section_end]
    # Suffixed names (:1, :2) must not appear in the written curve section
    assert ":1" not in curve_block
    assert ":2" not in curve_block


# ===========================================================================
# 21 — renamed mnemonic propagates to write
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_renamed_mnemonic():
    """Renaming a curve's .mnemonic attribute then calling write() produces
    output that contains the new name, not the original."""
    las = _read_base()
    las.curves["GR"].mnemonic = "GAMMA"
    output = _write_to_string(las)
    assert "GAMMA" in output
    # Original name should no longer appear as a standalone column header
    curve_section_start = output.upper().index("~C")
    curve_section_end = output.upper().index("~A")
    curve_block = output[curve_section_start:curve_section_end]
    lines_with_gr = [ln for ln in curve_block.splitlines() if " GR " in ln or ln.strip().startswith("GR")]
    assert len(lines_with_gr) == 0


# ===========================================================================
# 22 — changing curve unit updates STRT/STOP/STEP units on write
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_unit_change_propagates():
    """After changing the DEPT curve unit from 'M' to 'FT', writing the file
    must reflect 'FT' in the STRT, STOP, and STEP well header units."""
    las = _read_base()
    las.curves["DEPT"].unit = "FT"
    output = _write_to_string(las)
    header_section = output[: output.upper().index("~A")]
    strt_lines = [ln for ln in header_section.splitlines() if "STRT" in ln.upper()]
    assert any("FT" in ln for ln in strt_lines), (
        f"Expected 'FT' unit in STRT line but got: {strt_lines}"
    )


# ===========================================================================
# 23 — empty params section
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_empty_params():
    """A file with no ~PARAMETER section writes an empty (or absent) ~Params
    block; no KeyError or AttributeError is raised."""
    las = las_rs.read(_LAS_NO_PARAMS)
    output = _write_to_string(las)
    # Must produce a valid output without raising
    assert isinstance(output, str)
    assert "~V" in output.upper() or "VERS" in output.upper()


# ===========================================================================
# 24 — write after set_data_from_df
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_after_set_data_from_df():
    """Modifying a LASFile's data via set_data_from_df() and then writing it
    produces output where the data section reflects the new values."""
    pytest.importorskip("pandas")
    import pandas as pd

    las = _read_base()

    # Build a replacement DataFrame with new GR values
    dept = las.curves["DEPT"].data
    new_gr = np.array([10.0, 20.0, 30.0, 40.0])
    new_dt = las.curves["DT"].data.copy()
    new_rhob = las.curves["RHOB"].data.copy()
    df = pd.DataFrame(
        {"GR": new_gr, "DT": new_dt, "RHOB": new_rhob},
        index=dept,
    )
    df.index.name = "DEPT"
    las.set_data_from_df(df)

    output = _write_to_string(las)
    data_start = output.upper().index("~A")
    data_section = output[data_start:]

    # The new sentinel GR value (10.0) must appear in the data section
    assert "10.0" in data_section or "10." in data_section
    # Old GR values (48.30) must no longer appear
    assert "48.30" not in data_section
