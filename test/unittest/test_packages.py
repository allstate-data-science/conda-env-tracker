"""Test functions from packages.py"""

from conda_env_tracker.channels import Channels
from conda_env_tracker.env import Environment
from conda_env_tracker.history import (
    Actions,
    Debug,
    Diff,
    History,
    Logs,
    PackageRevision,
)
from conda_env_tracker.packages import get_packages, Package, Packages

ENV_NAME = "test-env"


def test_get_packages_conda(mocker):
    dependencies = {
        "conda": {
            "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            "numpy": Package("numpy", "numpy", "0.13", "py_36"),
        }
    }
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    packages = (Package.from_spec("pandas"),)
    local_history = History.create(
        name=ENV_NAME,
        packages=PackageRevision.create(packages, dependencies=dependencies),
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
        diff=Diff(),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    expected = {"conda": [Package("pandas", "pandas", "0.23", "py_36")]}
    actual = get_packages(env)
    assert actual == expected


def test_get_packages_pip(mocker):
    dependencies = {
        "conda": {
            "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            "numpy": Package("numpy", "numpy", "0.13", "py_36"),
        },
        "pip": {"pytest": Package("pytest", "pytest", "4.0")},
    }
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    local_packages = PackageRevision.create(
        (Package.from_spec("pandas"),), dependencies=dependencies
    )
    local_packages.update_packages(
        packages=(Package.from_spec("pytest"),), source="pip"
    )
    local_history = History.create(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
        diff=Diff(),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    expected = {
        "conda": [Package("pandas", "pandas", "0.23", "py_36")],
        "pip": [Package("pytest", "pytest", "4.0")],
    }
    actual = get_packages(env)
    assert actual == expected


def test_get_packages_with_version_spec(mocker):
    dependencies = {
        "conda": {
            "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            "numpy": Package("numpy", "numpy", "0.13", "py_36"),
        },
        "pip": {"pytest": Package("pytest", "pytest", "4.0")},
    }
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    local_packages = PackageRevision.create(
        (Package.from_spec("pandas=0.23"),), dependencies=dependencies
    )
    local_packages.update_packages(
        packages=(Package.from_spec("pytest==4.0"),), source="pip"
    )
    local_history = History.create(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
        diff=Diff(),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    expected = {
        "conda": [Package("pandas", "pandas=0.23", "0.23", "py_36")],
        "pip": [Package("pytest", "pytest==4.0", "4.0")],
    }
    actual = get_packages(env)
    assert actual == expected


def test_get_packages_r(mocker):
    dependencies = {
        "conda": {
            "r-base": Package("r-base", "r-base", "3.5.1", "h539"),
            "r-devtools": Package("r-devtools", "r-devtools", "0.1.0", "r351_0"),
        }
    }
    r_dependencies = {
        "trelliscopejs": Package("trelliscopejs", "trelliscopejs" "0.1.0")
    }
    mocker.patch("conda_env_tracker.env.get_dependencies", return_value=dependencies)
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies", return_value=r_dependencies
    )
    local_packages = PackageRevision.create(
        Packages((Package.from_spec("r-base"), Package.from_spec("r-devtools"))),
        dependencies=dependencies,
    )
    local_packages.update_packages(
        packages=(Package.from_spec("trelliscopejs"),), source="r"
    )
    local_history = History.create(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
        diff=Diff(),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    expected = {
        "conda": [
            Package("r-base", "r-base", "3.5.1", "h539"),
            Package("r-devtools", "r-devtools", "0.1.0", "r351_0"),
        ],
        "r": [Package("trelliscopejs", "trelliscopejs", "0.1.0")],
    }
    actual = get_packages(env)
    assert actual == expected
