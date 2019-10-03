"""Test the validation of arguments to main.py"""

import pytest

from conda_env_tracker.env import Environment
from conda_env_tracker.errors import PipInstallError, RError
from conda_env_tracker.validate import (
    check_pip,
    check_r_base_package,
    validate_remote_if_missing,
)


def test_missing_r_base():
    with pytest.raises(RError) as err:
        env = Environment.read(name="test_env_name_that_does_not_exist")
        check_r_base_package(env=env)
    assert (
        str(err.value)
        == f'"r-base" not installed.\nFound conda packages:\n[]\nMust have "r-base" conda installed to install R packages.'
    )


def test_missing_pip_pip_install():
    env = Environment.read(name="test_env_name_that_does_not_exist")
    env.dependencies = {"conda": {"python": "3.7"}}
    with pytest.raises(PipInstallError) as err:
        check_pip(env=env)
    assert str(err.value) == ("Must have pip installed to install pip packages")


@pytest.mark.parametrize("if_missing", [False, True])
def test_validate_if_missing(mocker, if_missing):
    if if_missing:
        with pytest.raises(SystemExit):
            validate_remote_if_missing(
                env_io=mocker.Mock(),
                remote_dir="/path/to/new/remote",
                yes=False,
                if_missing=if_missing,
            )
    else:
        validate_remote_if_missing(
            env_io=mocker.Mock(),
            remote_dir="/path/to/new/remote",
            yes=False,
            if_missing=if_missing,
        )
