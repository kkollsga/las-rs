"""
Phase 3 tests — Null value replacement policies.

Covers the strict, none, common, aggressive, all, and custom null policies as
well as the run-on hyphen/dot read policies and the effect of an empty
read_policy tuple.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(fn):
    return os.path.join(test_dir, "fixtures", fn)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NULL_FIXTURE = fixture("edge_cases/null_policy.las")
# null_policy.las has NULL=-999.25 and columns DEPT, GR, RHOB.
# Row values (DEPT, GR, RHOB):
#   100.0  -999.25   2.470
#   101.0   9999.0   2.512
#   102.0  -0.0733   2.634
#   103.0   9999.0  -999.25
#   104.0   42.15    2.500


# ---------------------------------------------------------------------------
# strict policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_strict_replaces_header_null():
    """strict null policy replaces exactly the NULL header value (-999.25)
    with NaN."""
    las = las_rs.read(NULL_FIXTURE, null_policy="strict")
    gr = las.curves["GR"].data
    # Row 0: GR=-999.25 → should become NaN
    assert np.isnan(gr[0])


@pytest.mark.xfail(reason="not yet implemented")
def test_null_strict_keeps_other():
    """strict null policy does NOT replace 9999.0 — only the exact NULL
    header value is substituted."""
    las = las_rs.read(NULL_FIXTURE, null_policy="strict")
    gr = las.curves["GR"].data
    # Row 1: GR=9999.0 — must be preserved
    assert not np.isnan(gr[1])
    assert gr[1] == pytest.approx(9999.0)


# ---------------------------------------------------------------------------
# none policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_none_keeps_all():
    """null_policy='none' keeps -999.25 as a raw float — no NaN replacement
    at all."""
    las = las_rs.read(NULL_FIXTURE, null_policy="none")
    gr = las.curves["GR"].data
    assert not np.isnan(gr[0])
    assert gr[0] == pytest.approx(-999.25)


# ---------------------------------------------------------------------------
# common policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_common_replaces_999_25():
    """common null policy replaces the canonical -999.25 sentinel with NaN."""
    las = las_rs.read(NULL_FIXTURE, null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


@pytest.mark.xfail(reason="not yet implemented")
def test_null_common_replaces_dashes():
    """common null policy replaces a bare dash ('-') text value with NaN."""
    # Build an in-memory LAS string with a dash in the data column.
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : WRAP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. DASH-TEST : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M   : DEPTH\n"
        " GR  .GAPI: GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0   -\n"
        " 2.0   45.0\n"
    )
    las = las_rs.read(las_text, null_policy="common")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])
    assert gr[1] == pytest.approx(45.0)


@pytest.mark.xfail(reason="not yet implemented")
def test_null_common_keeps_9999():
    """common null policy does NOT replace 9999 — that sentinel belongs to
    the aggressive policy."""
    las = las_rs.read(NULL_FIXTURE, null_policy="common")
    gr = las.curves["GR"].data
    # Row 1: GR=9999.0 — common must preserve it
    assert not np.isnan(gr[1])
    assert gr[1] == pytest.approx(9999.0)


# ---------------------------------------------------------------------------
# aggressive policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_aggressive_replaces_9999():
    """aggressive null policy replaces 9999 with NaN (in addition to
    the common sentinels)."""
    las = las_rs.read(NULL_FIXTURE, null_policy="aggressive")
    gr = las.curves["GR"].data
    # Row 1 and Row 3: GR=9999.0 → NaN
    assert np.isnan(gr[1])
    assert np.isnan(gr[3])


@pytest.mark.xfail(reason="not yet implemented")
def test_null_aggressive_keeps_small_negative():
    """aggressive null policy does NOT replace realistic small negative values
    such as -0.0733."""
    las = las_rs.read(NULL_FIXTURE, null_policy="aggressive")
    gr = las.curves["GR"].data
    # Row 2: GR=-0.0733 — must remain as-is
    assert not np.isnan(gr[2])
    assert gr[2] == pytest.approx(-0.0733)


# ---------------------------------------------------------------------------
# all policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_all_replaces_text():
    """all null policy replaces non-numeric text values with NaN."""
    las_text = (
        "~VERSION INFORMATION\n"
        " VERS.   2.0 : LAS VERSION 2.0\n"
        " WRAP.    NO : WRAP\n"
        "~WELL INFORMATION\n"
        " STRT.M   1.0 : START\n"
        " STOP.M   2.0 : STOP\n"
        " STEP.M   1.0 : STEP\n"
        " NULL. -999.25 : NULL\n"
        " WELL. ALL-TEST : WELL\n"
        "~CURVE INFORMATION\n"
        " DEPT.M   : DEPTH\n"
        " GR  .GAPI: GAMMA RAY\n"
        "~ASCII LOG DATA\n"
        " 1.0   IND\n"
        " 2.0   45.0\n"
    )
    las = las_rs.read(las_text, null_policy="all")
    gr = las.curves["GR"].data
    assert np.isnan(gr[0])


@pytest.mark.xfail(reason="not yet implemented")
def test_null_all_keeps_valid():
    """all null policy preserves valid numeric data that is not a known
    sentinel."""
    las = las_rs.read(NULL_FIXTURE, null_policy="all")
    rhob = las.curves["RHOB"].data
    # Row 0: RHOB=2.470 — must remain
    assert not np.isnan(rhob[0])
    assert rhob[0] == pytest.approx(2.470)


# ---------------------------------------------------------------------------
# Custom null policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_null_custom_list():
    """A custom null_policy list catches both a user-specified value (9998)
    and the NULL header value (-999.25)."""
    las = las_rs.read(fixture("edge_cases/custom_null.las"), null_policy=[-999.25, 9998])
    gr = las.curves["GR"].data
    # Row 0: GR=-999.25 → NaN
    assert np.isnan(gr[0])
    # Row 1 and Row 3: GR=9998.0 → NaN
    assert np.isnan(gr[1])
    assert np.isnan(gr[3])
    # Row 2: GR=42.15 → preserved
    assert gr[2] == pytest.approx(42.15)


# ---------------------------------------------------------------------------
# run-on policies
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_runon_dot_replaced():
    """run-on(.) read policy replaces a multi-decimal value like '1.2.3'
    with NaN because it cannot be a valid float."""
    las = las_rs.read(
        fixture("edge_cases/runon.las"),
        read_policy="run-on(.)",
    )
    rhob = las.curves["RHOB"].data
    # Row 1: RHOB='1.2.3' → NaN
    assert np.isnan(rhob[1])


# ---------------------------------------------------------------------------
# Empty read_policy
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="not yet implemented")
def test_read_policy_empty():
    """read_policy=() disables ALL regex substitutions; raw data text is
    passed to the numeric parser without any pre-processing."""
    # With an empty policy the comma decimal file is NOT converted, so the
    # parser will fail to read '1671,000' as a float (or produce NaN).
    las = las_rs.read(
        fixture("edge_cases/comma_decimal.las"),
        read_policy=(),
    )
    dept = las.curves["DEPT"].data
    # Without comma-decimal substitution the value cannot be a valid float,
    # so it should be NaN (or the parser raises an error caught by xfail).
    assert np.isnan(dept[1]) or dept[1] != pytest.approx(1671.0)
