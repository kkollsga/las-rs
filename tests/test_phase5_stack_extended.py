"""
Phase 5 extended: stack_curves edge cases.

Covers calling stack_curves() with no arguments, an empty element inside a
list, a missing mnemonic inside a list (with an informative KeyError), and
stacking a single-matching curve stub.

All tests are marked xfail because the `las_rs` Rust extension has not yet
been implemented.
"""

import os

import numpy as np
import pytest

import las_rs

test_dir = os.path.dirname(__file__)


def fixture(*parts):
    return os.path.join(test_dir, "fixtures", *parts)


# ---------------------------------------------------------------------------
# Inline LAS with curves: DEPT, GR, CBP1, CBP2, CBP3.
# 4 rows, deliberately different values from the existing stack_curves tests.
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  1500.0 : START DEPTH
 STOP.M  1503.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  IRONCLAD RESOURCES LTD : COMPANY
 WELL.  HAMMERHEAD-4 #1        : WELL NAME
~CURVE INFORMATION
 DEPT .M    : MEASURED DEPTH
 GR   .GAPI : GAMMA RAY
 CBP1 .US   : CEMENT BOND PEAK 1
 CBP2 .US   : CEMENT BOND PEAK 2
 CBP3 .US   : CEMENT BOND PEAK 3
~ASCII LOG DATA
 1500.0   34.55   210.1   220.2   230.3
 1501.0   47.88   215.5   225.6   235.7
 1502.0   61.22   209.9   219.0   229.1
 1503.0   53.11   212.3   222.4   232.5
"""

N_ROWS = 4


def _read():
    return las_rs.read(_LAS_SRC)


# ===========================================================================
# 1. stack_curves() with no arguments raises TypeError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_no_args_raises_typeerror():
    """stack_curves() called with no positional arguments raises TypeError
    because the required argument (curve selector) is missing."""
    las = _read()
    with pytest.raises(TypeError):
        las.stack_curves()


# ===========================================================================
# 2. stack_curves with an empty string element in the list raises ValueError
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_list_with_empty_element_raises():
    """stack_curves(['CBP1', '']) raises ValueError because an empty string is
    not a valid mnemonic inside the explicit list."""
    las = _read()
    with pytest.raises(ValueError):
        las.stack_curves(["CBP1", ""])


# ===========================================================================
# 3. stack_curves with missing mnemonic in list raises KeyError naming it
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_missing_in_list_keyerror_message():
    """stack_curves(['CBP1', 'BOGUS']) raises KeyError because 'BOGUS' is not a
    curve in the file.  The exception message should mention 'BOGUS' so the
    user knows which mnemonic was not found."""
    las = _read()
    with pytest.raises(KeyError) as exc_info:
        las.stack_curves(["CBP1", "BOGUS"])
    assert "BOGUS" in str(exc_info.value)


# ===========================================================================
# 4. stack_curves with a stub matching exactly one curve returns 2D array
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_single_match():
    """stack_curves('GR') when only one 'GR' curve exists returns a 2-D numpy
    array with shape (n_rows, 1) — even a single-column result must be 2-D."""
    las = _read()
    result = las.stack_curves("GR")
    assert isinstance(result, np.ndarray)
    assert result.ndim == 2
    assert result.shape == (N_ROWS, 1)
    np.testing.assert_array_almost_equal(result[:, 0], las["GR"])
