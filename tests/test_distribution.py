"""Distribution metadata must expose the intended name and complete license."""

from importlib.metadata import distribution


def test_installed_distribution_metadata() -> None:
    package = distribution("daybrief")
    assert package.metadata["Name"] == "daybrief"
    assert package.metadata["Requires-Python"] == ">=3.12"
    assert package.metadata["License-Expression"] == "MIT"
