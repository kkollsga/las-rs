"""
Phase 2 tests — Header line parsing.

Tests the function (or equivalent behavior) that turns a raw LAS header line
into a structured dict with keys: ``name``, ``unit``, ``value``, ``descr``.

Where the internal ``read_header_line`` function is not publicly exposed the
tests verify the same semantics indirectly by reading LAS files that contain
the relevant edge-case patterns and inspecting the parsed header items.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.
"""

import os

import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(fn):
    """Return the absolute path to a file under tests/fixtures/."""
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Helper: call read_header_line if exposed, otherwise skip the direct test
# ---------------------------------------------------------------------------

def _parse_line(line):
    """Call ``las_rs.reader.read_header_line`` if available.

    Returns a dict with keys ``name``, ``unit``, ``value``, ``descr``.
    Raises AttributeError if the function is not yet exposed so the test
    will still xfail correctly.
    """
    return las_rs.reader.read_header_line(line)


# ===========================================================================
# Direct parsing tests (via las_rs.reader.read_header_line)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_standard_line():
    """A canonical 'MNEM.UNIT VALUE : DESCRIPTION' line parses all four fields."""
    result = _parse_line("DEPT.M  : DEPTH")
    assert result["name"] == "DEPT"
    assert result["unit"] == "M"
    # Value field is empty in this line
    assert result["value"].strip() == ""
    assert "DEPTH" in result["descr"]


@pytest.mark.xfail(reason="not yet implemented")
def test_value_and_descr():
    """A line with a numeric value and a description parses all four fields."""
    result = _parse_line("BHT .DEGC  42.0 : BOTTOM HOLE TEMP")
    assert result["name"].strip() == "BHT"
    assert result["unit"] == "DEGC"
    assert result["value"].strip() == "42.0"
    assert "BOTTOM HOLE TEMP" in result["descr"]


@pytest.mark.xfail(reason="not yet implemented")
def test_empty_unit():
    """A line whose mnemonic has no unit (bare period) parses with unit=''."""
    result = _parse_line("COMP.  ACME INC : COMPANY")
    assert result["name"].strip() == "COMP"
    assert result["unit"].strip() == ""
    assert "ACME INC" in result["value"] or "ACME INC" in result["descr"]


@pytest.mark.xfail(reason="not yet implemented")
def test_line_without_period():
    """A header line that has a colon but no period still produces a name."""
    # Some LAS files omit the dot entirely: 'COMP  ACME : COMPANY'
    result = _parse_line("COMP  ACME CORP : COMPANY NAME")
    assert result["name"].strip() != ""


# ===========================================================================
# Indirect tests — read files, inspect parsed header items
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_bracketed_unit():
    """Units wrapped in square brackets are stripped to bare unit strings.

    File: edge_cases/bracketed_units.las  (curves have units like [M], [GAPI]).
    """
    las = las_rs.read(fixture("edge_cases/bracketed_units.las"))
    dept_unit = las.curves["DEPT"].unit
    gr_unit = las.curves["GR"].unit
    # Brackets must be removed — unit should be 'M' not '[M]'
    assert "[" not in dept_unit
    assert "]" not in dept_unit
    assert "(" not in gr_unit
    assert ")" not in gr_unit


@pytest.mark.xfail(reason="not yet implemented")
def test_colon_in_time_value():
    """A time value like '13:45:00' in the value field is preserved intact.

    File: edge_cases/colon_in_value.las  (params TLB and TLE contain HH:MM:SS).
    """
    las = las_rs.read(fixture("edge_cases/colon_in_value.las"))
    tlb = las.params["TLB"].value
    # The colon-separated time must not be split at the wrong colon
    assert ":" in tlb
    # Verify the time digits are present
    assert "13" in tlb and "45" in tlb


@pytest.mark.xfail(reason="not yet implemented")
def test_dot_in_mnemonic():
    """Mnemonics that end with a period (double-dot in file) are handled.

    File: edge_cases/dot_in_mnemonic.las  (params C.A. and REC. use double dots).
    """
    las = las_rs.read(fixture("edge_cases/dot_in_mnemonic.las"))
    # At least one param mnemonic should contain a trailing dot or be cleaned up;
    # the key requirement is that the file loads and the temperature param is found.
    param_mnemonics = [p.mnemonic for p in las.params]
    assert "BHT" in param_mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_v12_well_order():
    """In LAS 1.2, non-depth well items use descr:value order per the CWLS spec.

    For COMP in sample_v12.las the company name appears in the value field
    after the parser applies the version-specific field ordering.
    """
    las = las_rs.read(fixture("v12/sample_v12.las"))
    comp_value = las.well["COMP"].value
    assert "ACME DRILLING" in comp_value


@pytest.mark.xfail(reason="not yet implemented")
def test_v20_well_order():
    """In LAS 2.0, all well items use value:descr order.

    For COMP in sample_v20.las the company name is already in the value field.
    """
    las = las_rs.read(fixture("v20/sample_v20.las"))
    comp_value = las.well["COMP"].value
    assert "OCEANIC ENERGY" in comp_value


@pytest.mark.xfail(reason="not yet implemented")
def test_ignore_comment_lines():
    """Lines starting with '#' inside header sections are silently skipped.

    File: edge_cases/comment_lines.las  (# comments scattered through all sections).
    The file has comments in the ~VERSION, ~WELL, and ~CURVE sections; none
    of them should become HeaderItem entries.
    """
    las = las_rs.read(fixture("edge_cases/comment_lines.las"))
    # None of the section item mnemonics should start with '#'
    for section_items in [las.version, las.well, las.curves, las.params]:
        for item in section_items:
            assert not item.mnemonic.startswith("#")


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_upper():
    """mnemonic_case='upper' forces all parsed mnemonics to upper-case."""
    las = las_rs.read(
        fixture("v20/sample_v20.las"),
        mnemonic_case="upper",
    )
    for item in las.curves:
        assert item.mnemonic == item.mnemonic.upper()


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_lower():
    """mnemonic_case='lower' forces all parsed mnemonics to lower-case."""
    las = las_rs.read(
        fixture("v20/sample_v20.las"),
        mnemonic_case="lower",
    )
    for item in las.curves:
        assert item.mnemonic == item.mnemonic.lower()


@pytest.mark.xfail(reason="not yet implemented")
def test_mnemonic_case_preserve():
    """mnemonic_case='preserve' keeps mnemonics exactly as written in the file.

    sample_v20.las has 'DEPT', 'DT', 'GR', 'CALI', 'SP' — all upper-case.
    With preserve mode the exact characters from the file are used.
    """
    las = las_rs.read(
        fixture("v20/sample_v20.las"),
        mnemonic_case="preserve",
    )
    mnemonics = [c.mnemonic for c in las.curves]
    # The file writes them upper-case; preserve must not alter them
    assert "DEPT" in mnemonics
    assert "GR" in mnemonics
