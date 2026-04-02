"""
Shared pytest configuration and helpers for the las_rs test suite.

Provides a ``fixture_path`` helper function and a ``fixture`` pytest fixture
that resolve paths relative to the ``tests/fixtures/`` directory.  Tests may
import the helper directly or use the fixture via dependency injection.
"""

import os

import pytest

# Absolute path to the tests/fixtures directory.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_path(*parts: str) -> str:
    """Return the absolute path to a file inside tests/fixtures/.

    Accepts one or more path components that are joined with os.path.join,
    so both of the following forms work::

        fixture_path("v12", "sample_v12.las")
        fixture_path("v12/sample_v12.las")

    Parameters
    ----------
    *parts:
        One or more path components relative to ``tests/fixtures/``.

    Returns
    -------
    str
        Absolute path to the requested fixture file.
    """
    return os.path.join(FIXTURES_DIR, *parts)


@pytest.fixture
def fixture():
    """Pytest fixture that exposes the ``fixture_path`` helper.

    Usage inside a test::

        def test_something(fixture):
            path = fixture("v12", "sample_v12.las")
    """
    return fixture_path
