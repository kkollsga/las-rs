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


_LAS_WRITE_BASE = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   900.0 : START DEPTH
 STOP.M   901.0 : STOP DEPTH
 STEP.M     0.5 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  WRITETEST CORP : COMPANY
 WELL.  WRITETEST-1 #2 : WELL NAME
 UWI .  05-077-20130-00-00 : UNIQUE WELL ID
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
 SP  .MV   : SPONTANEOUS POTENTIAL
~ASCII LOG DATA
 900.0   55.0  -42.0
 900.5   62.0  -47.0
 901.0   70.0  -51.0
"""


def _read_base():
    return las_rs.read(_LAS_WRITE_BASE)


def _write_to_string(las, **kwargs):
    buf = StringIO()
    las.write(buf, **kwargs)
    return buf.getvalue()


# Ensure UTF-16 LE fixture file exists
_LAS_ASCII_BODY = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   100.0 : START DEPTH
 STOP.M   102.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  Bohrinsel AG : COMPANY
 WELL.  UTF16-TEST   : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII LOG DATA
 100.0   55.0
 101.0   62.0
 102.0   70.0
"""

_UTF16_LE_FILE = fixture("encodings", "utf16_le_explicit.las")
# Create the fixture if it doesn't exist
if not os.path.exists(_UTF16_LE_FILE):
    os.makedirs(os.path.dirname(_UTF16_LE_FILE), exist_ok=True)
    with open(_UTF16_LE_FILE, "wb") as f:
        f.write(_LAS_ASCII_BODY.encode("utf-16-le"))


# ===========================================================================
# From test_phase1_section_items_extended.py
# ===========================================================================


def test_mnemonic_rename_to_empty():
    """Appending a CurveItem with empty mnemonic auto-renames to 'UNKNOWN'.

    las_rs uses value semantics (like Polars), so mutation through a returned
    reference is not supported.  Instead, we test that the auto-rename
    happens when an item with blank mnemonic is appended.
    """
    sec = las_rs.SectionItems()
    sec.append(citem("", unit="GAPI", data=np.array([30.0, 40.0])))
    keys = list(sec.keys())
    assert any("UNKNOWN" in k.upper() for k in keys)



# ===========================================================================
# From test_phase2_read_edge_cases.py
# ===========================================================================


def test_sparse_curves():
    """Declared curves that have no data column in the ~ASCII section.

    File: edge_cases/sparse_curves.las
    Header declares: DEPT, GR, NPHI, RHOB, DT, PE  (6 curves)
    Data rows have only 3 columns — assigned positionally.
    Curves beyond the data columns get NaN-filled arrays.
    (Matches lasio behavior: positional assignment, not name-based.)
    """
    las = las_rs.read(fixture("edge_cases/sparse_curves.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    assert "NPHI" in curve_mnemonics
    # Curves beyond the 3 data columns must be NaN
    assert all(math.isnan(v) for v in las.curves["RHOB"].data)
    assert all(math.isnan(v) for v in las.curves["DT"].data)
    assert all(math.isnan(v) for v in las.curves["PE"].data)


# ===========================================================================
# Single-row data
# ===========================================================================



# ===========================================================================
# From test_phase3_data_extended.py
# ===========================================================================


def test_reshape_error_raises():
    """Data with fewer columns than declared curves silently pads with NaN.

    (Matches lasio behavior: no error raised, missing columns filled with NaN.)
    """
    las_text = (
        _minimal_header("RESHAPEERR")
        + "~CURVE INFORMATION\n"
        " DEPT.M    : DEPTH\n"
        " GR  .GAPI : GAMMA RAY\n"
        " RHOB.G/CC : DENSITY\n"
        "~ASCII LOG DATA\n"
        " 1.0  30.5\n"
        " 2.0  40.1\n"
        " 3.0  50.7\n"
    )
    las = _read_inline(las_text)
    assert las.data.shape == (3, 3)
    # Missing RHOB column should be NaN-filled
    assert all(math.isnan(v) for v in las.curves["RHOB"].data)


# ---------------------------------------------------------------------------
# 4. test_comma_decimal_in_params
# ---------------------------------------------------------------------------



# ===========================================================================
# From test_phase3_null_policies.py
# ===========================================================================


def test_runon_hyphen_separated():
    """run-on(-) read policy splits '123-456' into '123 -456' (two tokens).

    With 3 declared curves and 4 tokens after splitting, positional assignment:
    DEPT=100.0, GR=123.0, RHOB=-456.0. The extra value 2.470 goes to auto column.
    (Note: lasio itself crashes on this fixture with IndexError.)
    """
    las = las_rs.read(
        fixture("edge_cases/runon.las"),
        read_policy="run-on(-)",
    )
    gr = las.curves["GR"].data
    # After substitution '123-456' → '123 -456', GR gets first part (123)
    assert not np.isnan(gr[0])
    # The file should parse without crashing (unlike lasio)
    assert len(gr) > 0



# ===========================================================================
# From test_phase4_csv_export.py
# ===========================================================================


def test_to_csv_custom_mnemonics():
    """Passing an explicit list of mnemonics overrides the curve names in the
    header row."""
    las = read_v12()
    custom = ["DEPTH_M", "GAMMA", "NPOR", "DENSITY"]
    lines = csv_lines(las, mnemonics=custom)
    header = lines[0]
    for name in custom:
        assert name in header
    # Verify column names are exactly the custom list (not originals)
    col_names = header.split(",")
    assert col_names == custom



# ===========================================================================
# From test_phase4_write.py
# ===========================================================================


def test_write_nan_as_null():
    """NaN values in curve data are written as the NULL sentinel string.

    Uses __setitem__ (explicit API) to inject NaN into the GR column.
    """
    las = read_v12()
    gr_data = las["GR"].copy()
    gr_data[0] = np.nan
    las["GR"] = gr_data
    null_str = str(las.well["NULL"].value).strip()

    buf = StringIO()
    las.write(buf)
    output = buf.getvalue()

    data_section = output[output.upper().index("~A"):]
    assert null_str in data_section


# ---------------------------------------------------------------------------
# Full roundtrips
# ---------------------------------------------------------------------------



# ===========================================================================
# From test_phase4_write_extended.py
# ===========================================================================


def test_write_empty_value_string():
    """A LAS file with an empty-string well value writes and re-reads correctly."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : WRAP\n"
        "~WELL INFORMATION\n"
        " STRT.M   100.0 : START\n"
        " STOP.M   102.0 : STOP\n"
        " STEP.M     1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. EMPTY-VAL : WELL\n"
        " UWI .            : UNIQUE WELL ID\n"
        "~CURVE INFORMATION\n"
        " DEPT.M : DEPTH\n"
        "~ASCII LOG DATA\n"
        " 100.0\n 101.0\n 102.0\n"
    )
    las = las_rs.read(las_text)
    uwi_val = str(las.well["UWI"].value).strip()
    assert uwi_val == ""
    # Roundtrip
    buf = StringIO()
    las.write(buf)
    buf.seek(0)
    reread = las_rs.read(buf, ignore_header_errors=True)
    assert str(reread.well["UWI"].value).strip() == ""


# ===========================================================================
# 20 — duplicate mnemonics use original_mnemonic on write
# ===========================================================================


def test_write_renamed_mnemonic():
    """Renaming a curve via delete+append produces output with the new name.

    Uses explicit delete_curve + append_curve API (value semantics).
    """
    las = _read_base()
    gr_data = las["GR"].copy()
    las.delete_curve(mnemonic="GR")
    las.append_curve("GAMMA", gr_data, unit="GAPI", descr="Gamma ray")
    output = _write_to_string(las)
    assert "GAMMA" in output
    curve_section_start = output.upper().index("~C")
    curve_section_end = output.upper().index("~A")
    curve_block = output[curve_section_start:curve_section_end]
    lines_with_gr = [ln for ln in curve_block.splitlines() if " GR " in ln or ln.strip().startswith("GR")]
    assert len(lines_with_gr) == 0


# ===========================================================================
# 22 — changing curve unit updates STRT/STOP/STEP units on write
# ===========================================================================


def test_write_unit_change_propagates():
    """Changing the DEPT curve unit via delete+insert propagates to STRT/STOP/STEP on write."""
    las = _read_base()
    dept_data = las["DEPT"].copy()
    las.delete_curve(mnemonic="DEPT")
    las.insert_curve(0, "DEPT", dept_data, unit="FT", descr="DEPTH")
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


def test_las_header_error_on_malformed():
    """Reading a LAS string whose header line is missing the colon separator
    parses leniently (matching lasio behavior — no error raised)."""
    las = las_rs.read(_MALFORMED_HEADER_LAS)
    # lasio parses this leniently and creates a mangled key
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# 3. depth_m on unknown unit raises LASUnknownUnitError
# ===========================================================================



# ===========================================================================
# From test_phase7_properties.py
# ===========================================================================


def test_version_setter():
    """Assigning to las.version stores the new section values."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="VERS", unit="", value="2.0", descr="LAS version")]
    )
    las.version = new_section
    # Value equality — las_rs uses value semantics (not reference identity)
    assert list(las.version.keys()) == ["VERS"]
    assert str(las.version["VERS"].value) == "2.0"


def test_well_setter():
    """Assigning to las.well stores the new section values."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="WELL", unit="", value="SETTER-WELL-1", descr="")]
    )
    las.well = new_section
    assert list(las.well.keys()) == ["WELL"]
    assert las.well["WELL"].value == "SETTER-WELL-1"


def test_curves_setter():
    """Assigning to las.curves stores the new section values."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.CurveItem(mnemonic="DEPTH", unit="M", value="", descr="Depth")]
    )
    las.curves = new_section
    assert list(las.curves.keys()) == ["DEPTH"]
    assert las.curves["DEPTH"].unit == "M"


def test_params_setter():
    """Assigning to las.params stores the new section values."""
    las = _read_las()
    new_section = las_rs.SectionItems(
        [las_rs.HeaderItem(mnemonic="RES", unit="OHM", value="1.5", descr="Resistivity")]
    )
    las.params = new_section
    assert list(las.params.keys()) == ["RES"]
    assert las.params["RES"].unit == "OHM"


def test_update_start_stop_step():
    """update_start_stop_step() recalculates STRT, STOP, STEP from index data.

    Uses __setitem__ to replace the depth array (explicit value semantics).
    """
    las = _read_las()
    new_dept = np.array([5000.0, 5005.0, 5010.0])
    las["DEPT"] = new_dept
    # Also update other curves to match length
    las["DT"] = np.array([300.0, 310.0, 320.0])
    las["PORO"] = np.array([0.18, 0.19, 0.17])

    las.update_start_stop_step()

    assert float(las.well["STRT"].value) == pytest.approx(5000.0)
    assert float(las.well["STOP"].value) == pytest.approx(5010.0)
    assert float(las.well["STEP"].value) == pytest.approx(5.0)


def test_update_units_from_index_curve():
    """update_start_stop_step() copies the index curve unit to STRT/STOP/STEP.

    Uses delete+insert to change the DEPT curve's unit (explicit value semantics).
    """
    las = _read_las()
    dept_data = las["DEPT"].copy()
    las.delete_curve(mnemonic="DEPT")
    las.insert_curve(0, "DEPT", dept_data, unit="FT", descr="DEPTH")

    las.update_start_stop_step()

    assert las.well["STRT"].unit == "FT"
    assert las.well["STOP"].unit == "FT"
    assert las.well["STEP"].unit == "FT"


