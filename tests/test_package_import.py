"""Smoke tests for the package scaffold."""

import garmin_tcx_ai


def test_package_import() -> None:
    """The package can be imported from the src layout."""
    assert garmin_tcx_ai.__version__ == "0.1.0"
