"""
Phase 2 tests — Edge cases in LAS file reading.

Covers missing sections, blank lines, duplicate mnemonics, leading-zero
identifiers, excess/sparse data columns, single-row data, string columns,
and error-handling options.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.
"""

import math
import os

import numpy as np
import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(fn):
    """Return the absolute path to a file under tests/fixtures/."""
    return os.path.join(test_dir, "fixtures", fn)


# ===========================================================================
# Missing mandatory sections
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_missing_vers():
    """A file whose ~VERSION section omits the VERS line loads without error.

    File: edge_cases/missing_vers.las  (no VERS item; only WRAP).
    """
    las = las_rs.read(fixture("edge_cases/missing_vers.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_missing_wrap():
    """A file whose ~VERSION section omits the WRAP line loads without error.

    File: edge_cases/missing_wrap.las  (no WRAP item; only VERS 2.0).
    """
    las = las_rs.read(fixture("edge_cases/missing_wrap.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_missing_null():
    """A file whose ~WELL section omits the NULL line loads without error.

    File: edge_cases/missing_null.las  (no NULL item).
    """
    las = las_rs.read(fixture("edge_cases/missing_null.las"))
    assert isinstance(las, las_rs.LASFile)


@pytest.mark.xfail(reason="not yet implemented")
def test_missing_a_section():
    """A file that has no ~ASCII section produces an empty data array.

    File: edge_cases/missing_a_section.las  (header complete; no ~A block).
    """
    las = las_rs.read(fixture("edge_cases/missing_a_section.las"))
    assert isinstance(las, las_rs.LASFile)
    # Without any ~A section there is no data
    assert las.data.size == 0 or las.data.shape[0] == 0


# ===========================================================================
# Header-only file
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_header_only():
    """A file with an empty ~ASCII section yields zero-length curve arrays.

    File: edge_cases/header_only.las  (has ~A block header but no data rows).
    Curves defined: DEPT, GR, NPHI — each should have a zero-length data array.
    """
    las = las_rs.read(fixture("edge_cases/header_only.las"))
    assert isinstance(las, las_rs.LASFile)
    for curve in las.curves:
        assert len(curve.data) == 0


# ===========================================================================
# Blank lines
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_blank_line_in_header():
    """Blank lines inside header sections do not corrupt parsing.

    File: edge_cases/blank_line_in_header.las  (blank lines inside ~VERSION,
    ~WELL, and ~CURVE sections).  The file has 2 curves and 3 data rows.
    """
    las = las_rs.read(fixture("edge_cases/blank_line_in_header.las"))
    assert isinstance(las, las_rs.LASFile)
    assert len(las.curves) == 2
    assert las.data.shape[0] == 3


@pytest.mark.xfail(reason="not yet implemented")
def test_blank_line_at_start():
    """A file that starts with several blank lines before the first ~ still parses.

    File: edge_cases/blank_line_at_start.las  (4 leading blank lines before ~V).
    """
    las = las_rs.read(fixture("edge_cases/blank_line_at_start.las"))
    assert isinstance(las, las_rs.LASFile)
    assert float(las.version["VERS"].value) == pytest.approx(2.0)


# ===========================================================================
# Duplicate mnemonics
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_duplicate_mnemonics():
    """Two curves with the same mnemonic GR get unique suffixes GR:1 and GR:2.

    File: edge_cases/duplicate_mnemonics.las
    Curves: DEPT, GR (PRIMARY), GR (REPEAT), RHOB  — 3 data columns after DEPT.
    """
    las = las_rs.read(fixture("edge_cases/duplicate_mnemonics.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    # The two duplicate GR mnemonics must be disambiguated
    assert "GR:1" in curve_mnemonics or curve_mnemonics.count("GR") == 1
    # At least ensure no raw collision: unique count equals total count
    assert len(curve_mnemonics) == len(set(curve_mnemonics))


# ===========================================================================
# Empty / blank mnemonics
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_empty_mnemonic():
    """A curve with a blank mnemonic field is given the name 'UNKNOWN'.

    File: edge_cases/empty_mnemonic.las  (one curve with empty mnemonic).
    """
    las = las_rs.read(fixture("edge_cases/empty_mnemonic.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    assert "UNKNOWN" in curve_mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_multiple_empty_mnemonics():
    """Multiple curves with blank mnemonics become UNKNOWN:1 and UNKNOWN:2.

    File: edge_cases/multiple_empty_mnemonics.las  (two blank-mnemonic curves).
    """
    las = las_rs.read(fixture("edge_cases/multiple_empty_mnemonics.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    # Both unnamed curves must be uniquely named; common pattern is UNKNOWN:1, UNKNOWN:2
    unknown_entries = [m for m in curve_mnemonics if "UNKNOWN" in m.upper()]
    assert len(unknown_entries) == 2
    assert len(set(unknown_entries)) == 2  # must be distinct


# ===========================================================================
# Non-standard / custom sections
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_non_standard_section():
    """A custom ~CUSTOM TOOL INFORMATION section is stored in las.sections.

    File: edge_cases/non_standard_section.las  (contains ~CUSTOM TOOL INFORMATION).
    The custom section must be accessible via las.sections by its title (or a
    normalised variant).
    """
    las = las_rs.read(fixture("edge_cases/non_standard_section.las"))
    # sections dict must contain an entry for the custom section
    section_keys = [k.upper() for k in las.sections.keys()]
    custom_found = any("CUSTOM" in k for k in section_keys)
    assert custom_found


# ===========================================================================
# Malformed parameters
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_dodgy_params_raises():
    """A file with an unparseable parameter line raises LASHeaderError by default.

    File: edge_cases/dodgy_params.las  (one line '!!!INVALID…' in ~PARAMETER).
    """
    with pytest.raises(las_rs.LASHeaderError):
        las_rs.read(fixture("edge_cases/dodgy_params.las"))


@pytest.mark.xfail(reason="not yet implemented")
def test_dodgy_params_ignore():
    """With ignore_header_errors=True a malformed parameter line is skipped.

    File: edge_cases/dodgy_params.las  (one invalid line in ~PARAMETER section).
    The valid BHT and BS entries must still be present.
    """
    las = las_rs.read(
        fixture("edge_cases/dodgy_params.las"),
        ignore_header_errors=True,
    )
    param_mnemonics = [p.mnemonic for p in las.params]
    assert "BHT" in param_mnemonics
    assert "BS" in param_mnemonics


# ===========================================================================
# Leading-zero identifiers
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_uwi_leading_zero():
    """A UWI value that starts with a zero is stored as a string, not parsed as int.

    File: edge_cases/uwi_leading_zero.las  (UWI = 0512345678).
    """
    las = las_rs.read(fixture("edge_cases/uwi_leading_zero.las"))
    uwi_value = str(las.well["UWI"].value).strip()
    # Must begin with a zero — if parsed as a number the leading zero is lost
    assert uwi_value.startswith("0")


@pytest.mark.xfail(reason="not yet implemented")
def test_api_leading_zero():
    """An API number that starts with a zero is stored as a string.

    File: edge_cases/uwi_leading_zero.las  (API = 05-123-45678-00-00).
    """
    las = las_rs.read(fixture("edge_cases/uwi_leading_zero.las"))
    api_value = str(las.well["API"].value).strip()
    assert api_value.startswith("0")


# ===========================================================================
# Excess / sparse data columns
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_excess_data_columns():
    """Data rows with more columns than declared curves create auto-named curves.

    File: edge_cases/excess_data_columns.las
    Header declares: DEPT, GR  (2 curves, 2 columns expected)
    Data rows have:  DEPT, GR, RHOB, NPHI, PE  (5 columns — 3 extra)
    The extra columns should be stored under auto-generated names.
    """
    las = las_rs.read(fixture("edge_cases/excess_data_columns.las"))
    # More curves than the 2 declared in the header
    assert len(las.curves) > 2
    # All declared curves are present
    curve_mnemonics = [c.mnemonic for c in las.curves]
    assert "DEPT" in curve_mnemonics
    assert "GR" in curve_mnemonics


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


@pytest.mark.xfail(reason="not yet implemented")
def test_single_data_row():
    """A file with exactly one data row reads correctly (no reshape issues).

    File: edge_cases/single_data_row.las  (DEPT=250.0, GR=63.44, NPHI=0.228, RHOB=2.541).
    """
    las = las_rs.read(fixture("edge_cases/single_data_row.las"))
    assert las.data.shape[0] == 1
    dept_val = las.curves["DEPT"].data[0]
    assert dept_val == pytest.approx(250.0)


# ===========================================================================
# String data columns
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_string_data_columns():
    """A LAS 3.0 file with a {S} string column preserves string values.

    File: edge_cases/string_data_columns.las  (comma-delimited; LITHOLOGY is {S}).
    Lithology values: SANDSTONE, SHALE, LIMESTONE — must not be NaN.
    """
    las = las_rs.read(fixture("edge_cases/string_data_columns.las"))
    curve_mnemonics = [c.mnemonic for c in las.curves]
    assert "LITHOLOGY" in curve_mnemonics
    lith_data = las.curves["LITHOLOGY"].data
    # At least one string value must survive (non-empty, non-NaN)
    non_empty = [v for v in lith_data if v and str(v).strip() not in ("", "nan")]
    assert len(non_empty) > 0
    # Spot-check: first row should be SANDSTONE
    assert "SANDSTONE" in str(lith_data[0]).upper()
