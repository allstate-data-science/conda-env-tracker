"""Test PipHandler"""
# pylint: disable=redefined-outer-name
import copy

import pytest

from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.pip import PipHandler, PIP_DEFAULT_INDEX_URL


@pytest.mark.parametrize(
    "packages, pip_dependencies",
    [
        (
            Packages.from_specs("pytest"),
            {"pytest": Package("pytest", "pytest", "4.0.0")},
        ),
        (
            Packages.from_specs("pytest==4.0.0"),
            {"pytest": Package("pytest", "pytest==4.0.0", "4.0.0")},
        ),
        (
            Packages.from_specs(["pytest", "colorama"]),
            {
                "pytest": Package("pytest", "pytest", "4.0.0"),
                "colorama": Package("colorama", "colorama", "1.0.0"),
            },
        ),
    ],
)
def test_pip_install(setup_env, packages, pip_dependencies, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])
    get_package_mock = setup_env["get_package_mock"]
    initial_conda_packages = setup_env["initial_conda_packages"]

    get_package_mock.configure_mock(
        **{"return_value": {"conda": initial_conda_packages, "pip": pip_dependencies}}
    )
    mocker.patch("conda_env_tracker.pip.pip_install")

    PipHandler(env=env).install(packages=packages)

    install_command = f'pip install {" ".join(package.spec for package in packages)} --index-url {PIP_DEFAULT_INDEX_URL}'
    action_command = (
        f'pip install {" ".join(f"{name}=={package.version}" for name, package in pip_dependencies.items())}'
        f" --index-url {PIP_DEFAULT_INDEX_URL}"
    )
    expected["logs"].append(install_command)
    expected["packages"]["pip"] = pip_dependencies

    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == action_command


def test_pip_custom_install(setup_env, mocker):
    pip_package_url = "https://s3.amazonaws.com/h2o-release/h2o/master/4765/Python/h2o-3.26.0.4765-py2.py3-none-any.whl"
    pip_dependencies = {"h2o": Package("h2o", pip_package_url)}
    package = Package("h2o", pip_package_url)

    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])
    get_package_mock = setup_env["get_package_mock"]
    initial_conda_packages = setup_env["initial_conda_packages"]

    get_package_mock.configure_mock(
        **{"return_value": {"conda": initial_conda_packages, "pip": pip_dependencies}}
    )
    mocker.patch("conda_env_tracker.pip.pip_custom_install")

    PipHandler(env=env).custom_install(package=package)

    install_command = f"pip install {pip_package_url}"
    expected["logs"].append(install_command)
    expected["packages"]["pip"] = pip_dependencies
    action_command = install_command

    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == action_command


def test_pip_custom_install_github(setup_env, mocker):
    pip_package_url = "git+ssh://git@github.com/pandas-dev/pandas"
    pip_dependencies = {"pandas": Package("pandas", pip_package_url)}
    package = Package("pandas", pip_package_url)

    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])
    get_package_mock = setup_env["get_package_mock"]
    initial_conda_packages = setup_env["initial_conda_packages"]

    get_package_mock.configure_mock(
        **{"return_value": {"conda": initial_conda_packages, "pip": pip_dependencies}}
    )
    mocker.patch("conda_env_tracker.pip.pip_custom_install")

    PipHandler(env=env).custom_install(package=package)

    install_command = f"pip install {pip_package_url}"
    expected["logs"].append(install_command)
    expected["packages"]["pip"] = pip_dependencies
    action_command = install_command

    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == action_command


@pytest.fixture()
def setup_pip_env(setup_env, mocker):
    """Set up for pip remove"""
    pip_package_url = "git+ssh://git@github.com/pandas-dev/pandas"
    pip_dependencies = {
        "pandas": Package("pandas", pip_package_url),
        "pytest": Package("pytest", "pytest", "4.0.0"),
    }
    env = setup_env["env"]
    mocker.patch("conda_env_tracker.pip.pip_install")
    mocker.patch("conda_env_tracker.pip.pip_custom_install")
    get_package_mock = setup_env["get_package_mock"]
    initial_conda_packages = setup_env["initial_conda_packages"]
    get_package_mock.configure_mock(
        **{"return_value": {"conda": initial_conda_packages, "pip": pip_dependencies}}
    )
    PipHandler(env=env).install(packages=Packages.from_specs("pytest"))

    custom_package = Package("pandas", pip_package_url)
    PipHandler(env=env).custom_install(package=custom_package)

    return setup_env


def test_pip_remove(setup_pip_env, mocker):
    env = setup_pip_env["env"]
    env_io = setup_pip_env["env_io"]

    mocker.patch("conda_env_tracker.pip.pip_remove")
    PipHandler(env=env).remove(packages=Packages.from_specs("pytest"), yes=True)

    actual = env_io.get_history()

    assert actual.logs[-1] == "pip uninstall pytest"
    assert actual.actions[-1] == "pip uninstall pytest"
    assert actual.packages["pip"] == {
        "pandas": Package(
            name="pandas", spec="git+ssh://git@github.com/pandas-dev/pandas"
        )
    }

    PipHandler(env=env).remove(packages=Packages.from_specs("pandas"), yes=True)

    actual = env_io.get_history()
    assert actual.logs[-1] == "pip uninstall pandas"
    assert actual.actions[-1] == "pip uninstall pandas"
    assert "pip" not in actual.packages
