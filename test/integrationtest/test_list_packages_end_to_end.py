"""Test list packages from environment"""
from conda_env_tracker.main import pkg_list


def test_list_packages(end_to_end_setup):
    """Test the list packages in detail."""
    name = end_to_end_setup["name"]
    actual_packages = pkg_list(name)
    assert len(actual_packages) == 1
    assert len(actual_packages["conda"]) == 2
    assert actual_packages["conda"][0].name == "python"
    assert actual_packages["conda"][0].spec == "python=3.6"
    assert actual_packages["conda"][1].name == "colorama"
    assert actual_packages["conda"][1].spec == "colorama"
