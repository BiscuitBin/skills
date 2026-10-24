"""Proves the pytest wiring: the package imports from src/ and reports its version."""

import skills_tooling


def test_package_reports_its_version() -> None:
    assert skills_tooling.__version__ == "0.1.0"
