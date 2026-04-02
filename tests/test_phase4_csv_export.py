"""
Phase 4 tests — CSV export.

Covers the to_csv() method with all combinations of mnemonic headers, units
placement options (separate line, brackets, parentheses, omitted), and
explicit mnemonic list overrides.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
from io import StringIO

import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

V12_FILE = fixture("v12/sample_v12.las")


def read_v12():
    return las_rs.read(V12_FILE)


def csv_lines(las, **kwargs):
    """Call to_csv(**kwargs) on *las* and return the non-empty output lines."""
    buf = StringIO()
    las.to_csv(buf, **kwargs)
    return [l for l in buf.getvalue().splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# Basic output
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_basic():
    """to_csv() writes one data row per depth step; the number of data lines
    equals the number of rows in the LASFile's data array."""
    las = read_v12()
    lines = csv_lines(las)
    # The fixture has 6 depth steps; expect at least 6 data lines
    assert len(lines) >= 6


# ---------------------------------------------------------------------------
# Mnemonic header row
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_with_mnemonics():
    """mnemonics=True inserts a header row whose columns are the curve
    mnemonics."""
    las = read_v12()
    lines = csv_lines(las, mnemonics=True)
    header = lines[0]
    for curve in las.curves:
        assert curve.mnemonic in header


# ---------------------------------------------------------------------------
# Units placement — separate line
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_with_units_line():
    """units_loc='line' places units on a dedicated second line, separate
    from the mnemonics row."""
    las = read_v12()
    lines = csv_lines(las, mnemonics=True, units_loc="line")
    # With a separate units line there must be at least 2 header lines before
    # the first numeric row.
    assert len(lines) >= 2
    # The units line should contain the DEPT unit 'M' (or whatever the fixture
    # uses) but NOT any mnemonic like 'DEPT' unless they coincidentally match.
    units_line = lines[1]
    assert "M" in units_line  # DEPT unit from v12 fixture


# ---------------------------------------------------------------------------
# Units placement — brackets
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_with_units_brackets():
    """units_loc='[]' embeds units inside square brackets after each mnemonic
    (e.g. 'DEPT[M]')."""
    las = read_v12()
    lines = csv_lines(las, mnemonics=True, units_loc="[]")
    header = lines[0]
    # Depth curve should appear as DEPT[M] or similar
    assert "[" in header and "]" in header


# ---------------------------------------------------------------------------
# Units placement — parentheses
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_with_units_parens():
    """units_loc='()' embeds units inside parentheses after each mnemonic
    (e.g. 'DEPT(M)')."""
    las = read_v12()
    lines = csv_lines(las, mnemonics=True, units_loc="()")
    header = lines[0]
    assert "(" in header and ")" in header


# ---------------------------------------------------------------------------
# No units
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_to_csv_no_units():
    """units=False (or units_loc=None) omits any unit information from the
    output; the mnemonic row contains only bare mnemonics."""
    las = read_v12()
    lines = csv_lines(las, mnemonics=True, units=False)
    header = lines[0]
    # The unit 'GAPI' (GR unit in v12 fixture) must NOT appear in the header
    assert "GAPI" not in header
    # But the mnemonic itself must still be there
    assert "GR" in header


# ---------------------------------------------------------------------------
# Custom mnemonic list
# ---------------------------------------------------------------------------


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
