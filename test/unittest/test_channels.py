"""This tests functionality with conda channels"""
from conda_env_tracker.channels import Channels


def test_init_string():
    actual = Channels("conda-forge")
    expected = ["conda-forge"]

    assert actual == expected


def test_tuple_to_list():
    actual = Channels(("pro", "main"))
    expected = ["pro", "main"]
    assert actual == expected
