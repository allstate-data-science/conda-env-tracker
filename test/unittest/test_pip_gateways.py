"""Test pip interaction."""
from pathlib import Path
import subprocess

import pytest

from conda_env_tracker.gateways import pip
from conda_env_tracker.errors import PipInstallError
from conda_env_tracker.packages import Package


@pytest.mark.parametrize(
    "packages, index, expected",
    [
        (
            [Package.from_spec("pytest")],
            None,
            f"pip install pytest --index-url {pip.PIP_DEFAULT_INDEX_URL}",
        ),
        (
            [Package.from_spec("pytest==4.0.0")],
            "index-url",
            "pip install pytest==4.0.0 --index-url index-url",
        ),
        (
            [Package.from_spec("pytest"), Package.from_spec("colorama")],
            ["first-index", "second-index", "third-index"],
            "pip install pytest colorama --index-url first-index --extra-index-url second-index "
            "--extra-index-url third-index",
        ),
    ],
)
def test_pip_install_command(packages, index, expected):
    """Get the pip install command."""
    if index:
        actual = pip.get_pip_install_command(packages=packages, index=index)
    else:
        actual = pip.get_pip_install_command(packages=packages)
    assert actual == expected


@pytest.mark.parametrize(
    "name, packages, index, active_conda_env, expected",
    [
        (
            "env_name",
            [Package.from_spec("pytest")],
            None,
            "env_name",
            f"pip install pytest --index-url {pip.PIP_DEFAULT_INDEX_URL}",
        ),
        (
            "different_name",
            [Package.from_spec("pytest"), Package.from_spec("colorama")],
            "url",
            "env_name",
            f'source {Path.cwd().parent / "etc" / "profile.d" / "conda.sh"} && conda activate different_name && '
            "pip install pytest colorama --index-url url",
        ),
    ],
)
def test_pip_install_success(name, packages, index, active_conda_env, expected, mocker):
    """Successfully calling the install command"""
    run_mock = mocker.patch("conda_env_tracker.gateways.pip.subprocess.run")
    run_mock.configure_mock(**{"return_value.returncode": 0})
    mocker.patch(
        "conda_env_tracker.gateways.conda.get_conda_bin_path",
        mocker.Mock(return_value=Path.cwd()),
    )
    mocker.patch("os.environ.get", mocker.Mock(return_value=active_conda_env))

    if index:
        pip.pip_install(name=name, packages=packages, index_url=index)
    else:
        pip.pip_install(name=name, packages=packages)

    run_mock.assert_called_once_with(
        expected, shell=True, stderr=subprocess.PIPE, encoding="UTF-8"
    )


def test_pip_install_fail(mocker):
    name = "env_name"
    packages = [Package.from_spec("not_an_actual_pip_package")]

    run_mock = mocker.patch("conda_env_tracker.gateways.pip.subprocess.run")
    run_mock.configure_mock(
        **{"return_value.returncode": 1, "return_value.stderr": "error"}
    )
    mocker.patch("os.environ.get", mocker.Mock(return_value=name))

    with pytest.raises(PipInstallError) as err:
        pip.pip_install(name=name, packages=packages)
    assert (
        str(err.value)
        == "Pip install ['not_an_actual_pip_package'] failed with message: error"
    )


def test_pip_version(mocker):
    dep_mock = mocker.patch("conda_env_tracker.gateways.pip.get_dependencies")
    dep_mock.configure_mock(
        return_value={"conda": {"pip": Package("pip", "pip", "18.1", "py37_0")}}
    )

    version = pip.get_pip_version(name="env_name")

    assert version == "18.1"
