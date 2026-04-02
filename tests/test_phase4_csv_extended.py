"""
Phase 4 extended: CSV export edge cases.

Covers custom unit string overrides, alternative line terminators, and
custom mnemonic name overrides passed to to_csv().

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os
from io import StringIO

import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Inline LAS — 3 curves (DEPT, GR, CALI), 4 rows.
# Deliberately distinct from the existing CSV-export tests which use the
# v12 fixture file.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  2500.0 : START DEPTH
 STOP.M  2503.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  CRESTVIEW PETROLEUM : COMPANY
 WELL.  IRONHORSE-3 #7     : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 CALI.IN   : CALIPER
~ASCII LOG DATA
 2500.0   66.33   8.51
 2501.0   79.88   8.73
 2502.0   58.14   8.42
 2503.0   72.55   8.60
"""


def _read():
    return las_rs.read(_LAS_SRC)


def _csv_text(las, **kwargs):
    """Call las.to_csv(**kwargs) into a StringIO and return the raw string."""
    buf = StringIO()
    las.to_csv(buf, **kwargs)
    return buf.getvalue()


# ===========================================================================
# 1. to_csv with custom unit strings in the units argument
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_csv_custom_units():
    """to_csv(units=['meters', 'api', 'inches']) writes the supplied unit
    strings instead of the values stored in the CurveItem objects.  The
    custom strings must appear in the output."""
    las = _read()
    custom_units = ["meters", "api", "inches"]
    text = _csv_text(las, mnemonics=True, units=custom_units)
    assert "meters" in text
    assert "api" in text
    assert "inches" in text
    # Original unit labels must NOT appear when fully overridden.
    assert "GAPI" not in text
    assert "IN" not in text


# ===========================================================================
# 2. to_csv passes lineterminator through to csv.writer
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_csv_lineterminator():
    """to_csv(lineterminator='\\r\\n') produces output where every line ends
    with CRLF instead of a bare LF.  At least one '\\r\\n' sequence must appear
    in the raw output bytes."""
    las = _read()
    text = _csv_text(las, lineterminator="\r\n")
    assert "\r\n" in text


# ===========================================================================
# 3. to_csv with custom mnemonic names overrides headers
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_csv_custom_mnemonics():
    """to_csv(mnemonics=['Depth', 'Gamma', 'Caliper']) overrides the header row
    with the supplied names.  The custom names must appear and the original
    curve mnemonics must not."""
    las = _read()
    custom_mnemonics = ["Depth", "Gamma", "Caliper"]
    text = _csv_text(las, mnemonics=custom_mnemonics)
    for name in custom_mnemonics:
        assert name in text
    # Original mnemonics from the file must NOT appear in the header.
    assert "DEPT" not in text
    assert "GR" not in text
    assert "CALI" not in text
