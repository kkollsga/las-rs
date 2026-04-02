"""
Phase 6: LAS 3.0 support — multi-dataset, format fields, string columns, delimiters.

Covers reading LAS 3.0 files with multiple data sections (log, drilling, tops),
string-typed columns marked with ``{S}`` format codes, alternate column delimiters
(COMMA and TAB via the DLM field), and the section-name mapping rules that fold
``~Log_Definition`` into ``Curves`` and ``~Log_Parameter`` into ``Parameter``.

All tests are marked xfail because the ``las_rs`` implementation has not yet
been written.
"""

import os

import numpy as np
import pytest

import las_rs

# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Fixture file facts (tests/fixtures/v30/sample_v30.las)
#
#   VERS  = 3.0
#   DLM   = COMMA
#   ~Log_Parameter  → mapped to sections["Parameter"]
#   ~Log_Definition → mapped to sections["Curves"]
#   Curves: DEPT, GR, RHOB, NPHI, LITH  (LITH has {S} format)
#   Log data rows  : 3  (depths 1450, 1451, 1452)
#   Extra sections : Drilling_Definition / Drilling_ASCII_Standard
#                    Tops_Definition / Tops_ASCII_Standard
#   Params : BHT, BS, MWT
# ---------------------------------------------------------------------------

V30_FILE = fixture("v30", "sample_v30.las")
V30_TAB_FILE = fixture("v30", "sample_v30_tab.las")


# ===========================================================================
# Basic read
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_read_v30():
    """Reading a valid LAS 3.0 file returns a LASFile instance."""
    las = las_rs.read(V30_FILE)
    assert isinstance(las, las_rs.LASFile)


# ===========================================================================
# Version / DLM header items
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_version_value():
    """The VERS item in a LAS 3.0 file has value 3.0."""
    las = las_rs.read(V30_FILE)
    assert float(las.version["VERS"].value) == pytest.approx(3.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_dlm_value():
    """The DLM item in the version section has value 'COMMA'."""
    las = las_rs.read(V30_FILE)
    assert las.version["DLM"].value.strip().upper() == "COMMA"


# ===========================================================================
# Section-name mapping
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_curves_from_log_definition():
    """~Log_Definition is mapped to las.curves (sections['Curves'])."""
    las = las_rs.read(V30_FILE)
    # The Curves section must exist and contain the expected mnemonics.
    mnemonics = [c.mnemonic for c in las.curves]
    assert "DEPT" in mnemonics
    assert "GR" in mnemonics
    assert "LITH" in mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_params_from_log_parameter():
    """~Log_Parameter is mapped to las.params (sections['Parameter'])."""
    las = las_rs.read(V30_FILE)
    param_mnemonics = [p.mnemonic for p in las.params]
    assert "BHT" in param_mnemonics
    assert "MWT" in param_mnemonics


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_log_parameter_not_separate():
    """'Log_Parameter' does not appear as a standalone key in sections —
    it is merged into 'Parameter'."""
    las = las_rs.read(V30_FILE)
    assert "Log_Parameter" not in las.sections.keys()


# ===========================================================================
# Data shape
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_data_reads():
    """The main log data section has exactly 3 rows (depths 1450–1452)."""
    las = las_rs.read(V30_FILE)
    # las.data is a 2-D structure; the first dimension is the row count.
    assert las.data.shape[0] == 3


# ===========================================================================
# String columns
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_string_column():
    """The LITH column (marked {S}) contains string values, not only floats.

    The first row value is 'SANDSTONE', the last is 'SANDY SHALE'.
    """
    las = las_rs.read(V30_FILE)
    lith_data = las.curves["LITH"].data
    # At least one element must be a non-numeric string.
    str_values = [v for v in lith_data if isinstance(v, str)]
    assert len(str_values) > 0
    assert "SANDSTONE" in str_values or any("SAND" in s.upper() for s in str_values)


# ===========================================================================
# Non-standard (extra) sections
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_extra_sections_stored():
    """Non-standard sections such as Drilling_Definition and Tops_Definition
    are retained in the sections dictionary."""
    las = las_rs.read(V30_FILE)
    section_keys = list(las.sections.keys())
    # At least one drilling or tops section key must be present.
    has_drilling = any("drilling" in k.lower() for k in section_keys)
    has_tops = any("tops" in k.lower() for k in section_keys)
    assert has_drilling or has_tops


# ===========================================================================
# TAB delimiter
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_tab_delimiter_normal():
    """sample_v30_tab.las (DLM TAB) is read correctly with engine='normal'."""
    las = las_rs.read(V30_TAB_FILE, engine="normal")
    assert isinstance(las, las_rs.LASFile)
    # File has 3 log rows (depths 2100, 2101, 2102) and 5 curves.
    assert las.data.shape[0] == 3
    assert las.data.shape[1] == 5


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_tab_delimiter_numpy():
    """sample_v30_tab.las (DLM TAB) is read correctly with engine='numpy'."""
    las = las_rs.read(V30_TAB_FILE, engine="numpy")
    assert isinstance(las, las_rs.LASFile)
    assert las.data.shape[0] == 3


# ===========================================================================
# Comma-separated data values
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_v30_comma_data_parsed():
    """Numeric columns in the comma-delimited file parse to the correct floats.

    Row 0: DEPT=1450.0, GR=55.231, RHOB=2.512, NPHI=0.241
    Row 1: DEPT=1451.0, GR=78.645, RHOB=2.634, NPHI=0.198
    """
    las = las_rs.read(V30_FILE)
    dept = las.curves["DEPT"].data
    gr = las.curves["GR"].data
    rhob = las.curves["RHOB"].data
    nphi = las.curves["NPHI"].data

    assert dept[0] == pytest.approx(1450.0)
    assert gr[0] == pytest.approx(55.231)
    assert rhob[0] == pytest.approx(2.512)
    assert nphi[0] == pytest.approx(0.241)

    assert dept[1] == pytest.approx(1451.0)
    assert gr[1] == pytest.approx(78.645)
