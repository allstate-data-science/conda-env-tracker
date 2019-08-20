"""Integration test for utility functions"""
from conda_env_tracker.gateways.conda import init, CONDA_VERSION


def test_init_success():
    """Test that we can get the conda version."""
    init()
    assert CONDA_VERSION >= "4.4.10"
