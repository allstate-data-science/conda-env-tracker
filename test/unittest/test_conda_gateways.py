"""Test functions that interact with conda."""
# pylint: disable=redefined-outer-name

from pathlib import Path
import shutil

import pytest

from conda_env_tracker.gateways.conda import (
    get_all_existing_environment,
    get_dependencies,
    get_conda_channels,
    get_active_conda_env_name,
    init,
    update_conda_environment,
)
from conda_env_tracker.errors import CondaEnvTrackerCondaError
from conda_env_tracker.packages import Package


def test_init_failure(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    run_mock.configure_mock(
        **{"return_value.returncode": 1, "return_value.stderr": "error message"}
    )
    with pytest.raises(CondaEnvTrackerCondaError) as err:
        init()
    assert str(err.value) == (
        "Error checking conda version. Maybe you haven't installed anaconda/miniconda?\n"
        "Error: error message"
    )


def test_get_all_existing_environment_return_emptylist(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    attrs = {"return_value.stdout": "# stdout"}
    run_mock.configure_mock(**attrs)
    env_list = get_all_existing_environment()
    assert not env_list


def test_get_all_existing_environment_return_base(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    attrs = {"return_value.stdout": "# conda environments:\n#\nbase"}
    run_mock.configure_mock(**attrs)
    env_list = get_all_existing_environment()
    assert "base" in env_list
    assert len(env_list) == 1


@pytest.mark.parametrize(
    "pkg_list",
    (
        ("# packages in environment at /a/file\n" "#\n" "# Name Version Build Channel"),
        ("# packages in environment at /a/file\n" "#\n"),
    ),
)
def test_get_packages_empty(mocker, pkg_list):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    attrs = {
        "return_value.stdout": pkg_list,
        "return_value.stderr": None,
        "return_value.returncode": 0,
    }
    run_mock.configure_mock(**attrs)
    package_dict = get_dependencies("test-create")
    assert not package_dict["conda"]
    assert "pip" not in package_dict


@pytest.mark.parametrize(
    "packages",
    (
        (
            "# packages in environment at /a/file\n"
            "# Name Version Build Channel\n"
            "pylint 2.0.4 py37_0 conda-forge\n"
            "pytest\t1.0.7\tpy37_0\tconda-forge\n"
        ),
        ("pylint 2.0.4 py37_0 conda-forge\npytest 1.0.7 pypi"),
        ("pylint 2.0.4 py37_0 conda-forge\npytest 1.0.7 pip"),
    ),
)
def test_get_packages(mocker, packages):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    attrs = {
        "return_value.stdout": packages,
        "return_value.stderr": None,
        "return_value.returncode": 0,
    }
    run_mock.configure_mock(**attrs)

    actual = get_dependencies("test-create")

    expected = {"conda": {"pylint": Package("pylint", "pylint", "2.0.4", "py37_0")}}
    if packages.endswith("pypi") or packages.endswith("pip"):
        expected["pip"] = {"pytest": Package("pytest", "pytest", "1.0.7")}
    else:
        expected["conda"]["pytest"] = Package("pytest", "pytest", "1.0.7", "py37_0")
    assert actual == expected


def test_get_conda_channels_success(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    attrs = {
        "return_value.stdout": (
            "--add channels 'conda-forge'\n" "--add channels 'main'"
        )
    }
    run_mock.configure_mock(**attrs)
    channel_list = get_conda_channels()
    assert channel_list == ["main", "conda-forge"]


@pytest.fixture(scope="function")
def setup_env_dir(request, mocker):
    """Setup files for environment update."""
    env_dir = Path(__file__).parent / "env_dir"
    if not env_dir.exists():
        env_dir.mkdir()
    (env_dir / "environment.yml").touch()

    run_mock = mocker.patch("conda_env_tracker.gateways.conda.run_command")
    attrs = {"return_value.return_code": 0, "return_value.stdout": ""}
    run_mock.configure_mock(**attrs)

    def teardown():
        shutil.rmtree(env_dir)

    request.addfinalizer(teardown)
    return {
        "env_dir": env_dir,
        "run_mock": run_mock,
        "expected_file": "environment.yml",
    }


def test_update_env_from_file(setup_env_dir):
    env_dir = setup_env_dir["env_dir"]
    run_mock = setup_env_dir["run_mock"]
    expected_file = env_dir / setup_env_dir["expected_file"]

    update_conda_environment(env_dir=env_dir)
    run_mock.assert_called_once_with(
        f'conda env update --prune --file "{expected_file}"',
        error=CondaEnvTrackerCondaError,
    )


def test_update_env_error():
    env_dir = Path(__file__).parent

    with pytest.raises(CondaEnvTrackerCondaError) as err:
        update_conda_environment(env_dir=env_dir)
    assert str(err.value).startswith(
        f"No environment file to update from in {env_dir}."
    )


def test_get_active_conda_env_name(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.conda.subprocess.run")
    run_mock.configure_mock(**{"return_value.stdout": "env_name\n"})

    name = get_active_conda_env_name()

    assert name == "env_name"
