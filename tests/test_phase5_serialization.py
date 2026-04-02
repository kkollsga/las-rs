"""Phase 5 extended: Pickle serialization for all core types."""

import pickle

import numpy as np
import pytest

import las_rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_LAS = """\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M  3000.0 : START DEPTH
 STOP.M  3004.0 : STOP DEPTH
 STEP.M     1.0 : STEP VALUE
 NULL. -999.25  : NULL VALUE
 COMP.  MESA OIL CORP  : COMPANY
 WELL.  FLATROCK-11 #2 : WELL NAME
~CURVE INFORMATION
 DEPT.M    : MEASURED DEPTH
 GR  .GAPI : GAMMA RAY
 RHOB.G/CC : BULK DENSITY
~ASCII LOG DATA
 3000.0   48.31  2.508
 3001.0   62.74  2.490
 3002.0   77.08  2.533
 3003.0   55.20  2.461
 3004.0   41.65  2.576
"""


# ---------------------------------------------------------------------------
# 1. test_pickle_lasfile
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_pickle_lasfile():
    """pickle.dumps / pickle.loads round-trips a LASFile, preserving the
    version string, well section, curve names, and numeric data."""
    original = las_rs.read(_SIMPLE_LAS)
    blob = pickle.dumps(original)
    restored = pickle.loads(blob)

    # Version preserved
    assert float(restored.version["VERS"].value) == pytest.approx(
        float(original.version["VERS"].value)
    )
    # Well name preserved
    assert restored.well["WELL"].value == original.well["WELL"].value
    # Curve count preserved
    assert len(restored.curves) == len(original.curves)
    # Numeric data preserved
    np.testing.assert_array_almost_equal(
        restored.curves["GR"].data,
        original.curves["GR"].data,
    )
    np.testing.assert_array_almost_equal(
        restored.curves["DEPT"].data,
        original.curves["DEPT"].data,
    )


# ---------------------------------------------------------------------------
# 2. test_pickle_curveitem
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_pickle_curveitem():
    """pickle.dumps / pickle.loads round-trips a CurveItem, preserving all
    header fields and the data array."""
    samples = np.array([10.0, 20.5, 31.2, 42.8, 55.1])
    original = las_rs.CurveItem(
        mnemonic="SP",
        unit="MV",
        value="52 530 01 00 10",
        descr="Spontaneous potential",
        data=samples,
    )
    blob = pickle.dumps(original)
    restored = pickle.loads(blob)

    assert restored.mnemonic == "SP"
    assert restored.unit == "MV"
    assert restored.value == "52 530 01 00 10"
    assert restored.descr == "Spontaneous potential"
    np.testing.assert_array_almost_equal(restored.data, samples)


# ---------------------------------------------------------------------------
# 3. test_pickle_sectionitems
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_pickle_sectionitems():
    """pickle.dumps / pickle.loads round-trips a SectionItems, preserving all
    items and the mnemonic_transforms flag."""
    original = las_rs.SectionItems(mnemonic_transforms=True)
    original.append(las_rs.HeaderItem(mnemonic="WELL",  value="PICKLE-WELL"))
    original.append(las_rs.HeaderItem(mnemonic="FLD",   value="PICKLE-FIELD"))
    original.append(las_rs.HeaderItem(mnemonic="PROV",  value="PICKLE-PROVINCE"))

    blob = pickle.dumps(original)
    restored = pickle.loads(blob)

    assert len(restored) == 3
    assert list(restored.keys()) == ["WELL", "FLD", "PROV"]
    assert restored["WELL"].value == "PICKLE-WELL"
    assert restored["FLD"].value  == "PICKLE-FIELD"
    assert restored["PROV"].value == "PICKLE-PROVINCE"
    # mnemonic_transforms flag must be preserved
    assert restored.mnemonic_transforms is True
