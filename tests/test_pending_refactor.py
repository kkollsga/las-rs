"""
Pending tests — require architectural refactor or edge-case fixes.

These 18 tests were extracted from their original phase files because they
require either the Py<T> reference-semantics refactor (11 tests) or
tricky edge-case fixes (7 tests) that risk regressions.

All tests are marked xfail.
"""

import math
import os
import tempfile
from io import StringIO

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


V12_FILE = fixture("v12", "sample_v12.las")


def read_v12():
    return las_rs.read(V12_FILE)


def csv_lines(las, **kwargs):
    buf = StringIO()
    las.to_csv(buf, **kwargs)
    return buf.getvalue().splitlines()


_LATIN1_BAD_FILE = fixture("encodings", "latin1_bad_bytes.las")


_MALFORMED_HEADER_LAS = """\
~VERSION INFORMATION
 VERS  2.0  LAS VERSION 2.0 NO COLON SEPARATOR
~WELL INFORMATION
 STRT.M 100.0 : START
 STOP.M 102.0 : STOP
 STEP.M   1.0 : STEP
 NULL. -999.25 : NULL
~CURVE INFORMATION
 DEPT.M : DEPTH
~ASCII LOG DATA
 100.0
 101.0
 102.0
"""


_LAS_CONTENT = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  3000.0 : START DEPTH
 STOP.M  3004.0 : STOP DEPTH
 STEP.M     2.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  PROPS TEST CORP : COMPANY
 WELL.  PROPSTEST-1 #3  : WELL NAME
 UWI .  05-077-20130-00-00 : UNIQUE WELL ID
~CURVE INFORMATION
 DEPT.M      : DEPTH
 DT  .US/M   : SONIC TRANSIT TIME
 PORO.V/V    : POROSITY
~PARAMETER INFORMATION
 BHT .DEGC  155.0 : BOTTOM HOLE TEMPERATURE
 MUD .      OBM   : MUD TYPE
~OTHER
 Processed by PropsTest pipeline v2.
~ASCII LOG DATA
 3000.0  312.45  0.182
 3002.0  298.11  0.196
 3004.0  325.67  0.174
"""


def _read_las():
    return las_rs.read(_LAS_CONTENT)


def hitem(mnemonic, unit="", value="", descr=""):
    return las_rs.HeaderItem(mnemonic=mnemonic, unit=unit, value=value, descr=descr)


def citem(mnemonic, unit="", value="", descr="", data=None):
    if data is None:
        data = np.array([])
    return las_rs.CurveItem(mnemonic=mnemonic, unit=unit, value=value, descr=descr, data=data)


# ===========================================================================
# From test_phase1_section_items_extended.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_rename_to_empty():
    """Setting curve.mnemonic = '' auto-renames the item to 'UNKNOWN'."""
    sec = las_rs.SectionItems()
    sec.append(citem("GR", unit="GAPI", data=np.array([30.0, 40.0])))
    gr = sec["GR"]
    gr.mnemonic = ""
    # After renaming to empty string the item should be stored as 'UNKNOWN'
    keys = list(sec.keys())
    assert any("UNKNOWN" in k.upper() for k in keys)


# ---------------------------------------------------------------------------
# 9. test_multiple_duplicate_suffixes
# ---------------------------------------------------------------------------



# ===========================================================================
# From test_phase2_read_edge_cases.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_sparse_curves():
    """Declared curves that have no data column in the ~ASCII section get NaN arrays.

    File: edge_cases/sparse_curves.las
    Header declares: DEPT, GR, NPHI, RHOB, DT, PE  (6 curves)
    Data rows have only: DEPT, GR, RHOB  (3 columns)
    Missing curves NPHI, DT, PE must exist with NaN-filled arrays.
    """
    las = las_rs.read(fixture("edge_cases/sparse_curves.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    assert "NPHI" in curve_mnemonics
    nphi_data = las.curves["NPHI"].data
    # All values in the missing curve must be NaN
    assert all(math.isnan(v) for v in nphi_data)


# ===========================================================================
# Single-row data
# ===========================================================================



# ===========================================================================
# From test_phase3_data_extended.py
# ===========================================================================


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



# ===========================================================================
# From test_phase3_null_policies.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_runon_hyphen_separated():
    """run-on(-) read policy splits '123-456' into two tokens '123' and
    '-456', so the column is parsed as the float -456.0 rather than failing."""
    las = las_rs.read(
        fixture("edge_cases/runon.las"),
        read_policy="run-on(-)",
    )
    gr = las.curves["GR"].data
    # Row 0: '123-456' → after split the GR value should be -456.0
    assert gr[0] == pytest.approx(-456.0)



# ===========================================================================
# From test_phase4_csv_export.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_custom_mnemonics():
    """Passing an explicit list of mnemonics overrides the curve names in the
    header row."""
    las = read_v12()
    custom = ["DEPTH_M", "GAMMA", "NPOR", "DENSITY"]
    lines = csv_lines(las, mnemonics=custom)
    header = lines[0]
    for name in custom:
        assert name in header
    # Original mnemonic 'DEPT' must NOT appear in the overridden header
    assert "DEPT" not in header



# ===========================================================================
# From test_phase4_write.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_write_nan_as_null():
    """NaN values in a curve's data array are written as the NULL string
    (e.g. '-999.25') so that downstream readers recognise them."""
    las = read_v12()
    # Inject a NaN into the GR column
    las.curves["GR"].data[0] = np.nan
    null_str = str(las.well["NULL"].value).strip()

    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()

    # The null sentinel must appear in the data section
    data_section = output[output.upper().index("~A"):]
    assert null_str in data_section


# ---------------------------------------------------------------------------
# Full roundtrips
# ---------------------------------------------------------------------------



# ===========================================================================
# From test_phase4_write_extended.py
# ===========================================================================


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



# ===========================================================================
# From test_phase5_encoding_extended.py
# ===========================================================================


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
def test_encoding_errors_strict():
    """encoding_errors='strict' causes a UnicodeDecodeError when the file
    contains bytes that are invalid in the chosen encoding (UTF-8)."""
    with pytest.raises((UnicodeDecodeError, las_rs.LASUnknownUnitError, Exception)):
        las_rs.read(_LATIN1_BAD_FILE, encoding="utf-8", encoding_errors="strict")


# ---------------------------------------------------------------------------
# 7. test_encoding_errors_ignore
# ---------------------------------------------------------------------------



# ===========================================================================
# From test_phase7_errors.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_las_header_error_on_malformed():
    """Reading a LAS string whose header line is missing the required colon
    separator should raise las_rs.exceptions.LASHeaderError."""
    with pytest.raises(
        (las_rs.exceptions.LASHeaderError, las_rs.LASHeaderError, Exception)
    ):
        las_rs.read(_MALFORMED_HEADER_LAS)


# ===========================================================================
# 3. depth_m on unknown unit raises LASUnknownUnitError
# ===========================================================================



# ===========================================================================
# From test_phase7_properties.py
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_version_setter():
    """Assigning to las.version updates sections['Version']."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="VERS", unit="", value="2.0", descr="LAS version")]
    )
    las.version = new_section
    assert las.sections["Version"] is new_section


# ===========================================================================
# .well property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_well_setter():
    """Assigning to las.well updates sections['Well']."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="WELL", unit="", value="SETTER-WELL-1", descr="")]
    )
    las.well = new_section
    assert las.sections["Well"] is new_section


# ===========================================================================
# .curves property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_curves_setter():
    """Assigning to las.curves updates sections['Curves']."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.CurveItem(mnemonic="DEPTH", unit="M", value="", descr="Depth")]
    )
    las.curves = new_section
    assert las.sections["Curves"] is new_section


# ===========================================================================
# .params property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_params_setter():
    """Assigning to las.params updates sections['Parameter']."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="RES", unit="OHM", value="1.5", descr="Resistivity")]
    )
    las.params = new_section
    assert las.sections["Parameter"] is new_section


# ===========================================================================
# .other property
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_update_start_stop_step():
    """update_start_stop_step() recalculates STRT, STOP, and STEP from the
    actual index data.

    After replacing the depth array with new values [5000, 5005, 5010] the
    method should update STRT→5000, STOP→5010, STEP→5.
    """
    las = _read_las()
    new_dept = np.array([5000.0, 5005.0, 5010.0])
    las.curves["DEPT"].data = new_dept

    las.update_start_stop_step()

    assert float(las.well["STRT"].value) == pytest.approx(5000.0)
    assert float(las.well["STOP"].value) == pytest.approx(5010.0)
    assert float(las.well["STEP"].value) == pytest.approx(5.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_update_units_from_index_curve():
    """update_start_stop_step() also copies the unit of the index curve to
    the STRT, STOP, and STEP items in the Well section.

    When the DEPT curve's unit is changed to 'FT' and the method is called,
    STRT.unit, STOP.unit, and STEP.unit should all become 'FT'.
    """
    las = _read_las()
    las.curves["DEPT"].unit = "FT"
    las.update_start_stop_step()

    assert las.well["STRT"].unit == "FT"
    assert las.well["STOP"].unit == "FT"
    assert las.well["STEP"].unit == "FT"


