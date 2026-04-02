"""
Phase 5e tests — Multi-channel curve stacking.

Covers las.stack_curves() with a stub string, an explicit list, natural-sort
ordering (CBP1…CBP10), sort_curves=False, empty / missing inputs, and a
numpy-array of names.

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
# Inline LAS with multi-channel curves.
#
# DEPT + GR + CBP1…CBP4 + CBP10 = 7 curves, 4 rows.
# CBP10 is included so we can verify natural sort (1,2,3,4,10 not 1,10,2,3,4).
# ---------------------------------------------------------------------------

_LAS_SRC = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  3000.0 : START DEPTH
 STOP.M  3003.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  RIDGELINE PETROLEUM : COMPANY
 WELL.  MESA-ALTA-1 #5      : WELL NAME
~CURVE INFORMATION
 DEPT .M    : MEASURED DEPTH
 GR   .GAPI : GAMMA RAY
 CBP1 .US   : CHANNEL BOND PEAK 1
 CBP2 .US   : CHANNEL BOND PEAK 2
 CBP3 .US   : CHANNEL BOND PEAK 3
 CBP4 .US   : CHANNEL BOND PEAK 4
 CBP10.US   : CHANNEL BOND PEAK 10
~ASCII LOG DATA
 3000.0   45.11   120.1   130.2   140.3   150.4   200.10
 3001.0   58.77   121.5   131.6   141.7   151.8   201.50
 3002.0   72.33   119.9   129.0   139.1   149.2   199.90
 3003.0   50.22   122.3   132.4   142.5   152.6   202.30
"""

N_ROWS = 4


def _read():
    return las_rs.read(_LAS_SRC)


# ===========================================================================
# Stub-based stacking (all CBP* channels)
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_by_stub():
    """stack_curves('CBP') selects all curves whose mnemonic starts with 'CBP'
    and returns a 2-D numpy array."""
    las = _read()
    result = las.stack_curves("CBP")
    assert isinstance(result, np.ndarray)
    assert result.ndim == 2


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_by_stub_shape():
    """stack_curves('CBP') on a file with 5 CBP channels (CBP1-4 + CBP10)
    returns an array with shape (n_rows, 5)."""
    las = _read()
    result = las.stack_curves("CBP")
    assert result.shape == (N_ROWS, 5)


# ===========================================================================
# List-based stacking
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_by_list():
    """stack_curves(['CBP2', 'CBP4']) returns a 2-D array with exactly 2
    columns corresponding to those two curves."""
    las = _read()
    result = las.stack_curves(["CBP2", "CBP4"])
    assert result.shape == (N_ROWS, 2)
    # First column must match CBP2 data
    np.testing.assert_array_almost_equal(result[:, 0], las["CBP2"])
    # Second column must match CBP4 data
    np.testing.assert_array_almost_equal(result[:, 1], las["CBP4"])


# ===========================================================================
# Natural sort ordering
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_sorts_naturally():
    """When sorting by stub, CBP10 is placed after CBP4 (natural integer order
    1,2,3,4,10) rather than lexicographic order (1,10,2,3,4)."""
    las = _read()
    result = las.stack_curves("CBP")
    # The last column (index 4) should be CBP10 data, not CBP2.
    cbp10_data = las["CBP10"]
    np.testing.assert_array_almost_equal(result[:, 4], cbp10_data)


# ===========================================================================
# sort_curves=False
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_no_sort():
    """stack_curves('CBP', sort_curves=False) preserves the order in which
    CBP curves appear in las.curves (insertion order)."""
    las = _read()
    result = las.stack_curves("CBP", sort_curves=False)
    # Insertion order: CBP1, CBP2, CBP3, CBP4, CBP10
    np.testing.assert_array_almost_equal(result[:, 0], las["CBP1"])
    np.testing.assert_array_almost_equal(result[:, 4], las["CBP10"])


# ===========================================================================
# Error cases
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_empty_raises():
    """stack_curves('') raises ValueError because the stub is empty."""
    las = _read()
    with pytest.raises(ValueError):
        las.stack_curves("")


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_empty_list_raises():
    """stack_curves([]) raises ValueError because the list is empty."""
    las = _read()
    with pytest.raises(ValueError):
        las.stack_curves([])


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_missing_raises():
    """stack_curves('NONEXIST') raises KeyError when no curve matches the
    given stub."""
    las = _read()
    with pytest.raises(KeyError):
        las.stack_curves("NONEXIST")


# ===========================================================================
# numpy array of names as input
# ===========================================================================


@pytest.mark.xfail(reason="not yet implemented")
def test_stack_ndarray_input():
    """stack_curves(np.array(['CBP1', 'CBP2'])) works when the input is a
    numpy string array rather than a plain Python list."""
    las = _read()
    names = np.array(["CBP1", "CBP2"])
    result = las.stack_curves(names)
    assert result.shape == (N_ROWS, 2)
    np.testing.assert_array_almost_equal(result[:, 0], las["CBP1"])
    np.testing.assert_array_almost_equal(result[:, 1], las["CBP2"])
