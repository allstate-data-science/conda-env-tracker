"""Test functions from packages.py"""

from conda_env_tracker.channels import Channels
from conda_env_tracker.env import Environment
from conda_env_tracker.history import History, Logs, Actions, Debug, HistoryPackages
from conda_env_tracker.packages import get_packages, Package, Packages

ENV_NAME = "test-env"


def test_get_packages_conda(mocker):
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={
            "conda": {
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
                "numpy": Package("numpy", "numpy", "0.13", "py_36"),
            }
        },
    )
    packages = (Package.from_spec("pandas"),)
    local_history = History(
        name=ENV_NAME,
        packages=HistoryPackages.create(packages),
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    expected = {"conda": [Package("pandas", "pandas", "0.23", "py_36")]}
    actual = get_packages(env)
    assert actual == expected


def test_get_packages_pip(mocker):
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={
            "conda": {
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
                "numpy": Package("numpy", "numpy", "0.13", "py_36"),
            },
            "pip": {"pytest": Package("pytest", "pytest", "4.0")},
        },
    )
    local_packages = HistoryPackages.create((Package.from_spec("pandas"),))
    local_packages.update_packages(
        packages=(Package.from_spec("pytest"),), source="pip"
    )
    local_history = History(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
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
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={
            "conda": {
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
                "numpy": Package("numpy", "numpy", "0.13", "py_36"),
            },
            "pip": {"pytest": Package("pytest", "pytest", "4.0")},
        },
    )
    local_packages = HistoryPackages.create((Package.from_spec("pandas=0.23"),))
    local_packages.update_packages(
        packages=(Package.from_spec("pytest==4.0"),), source="pip"
    )
    local_history = History(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
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
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={
            "conda": {
                "r-base": Package("r-base", "r-base", "3.5.1", "h539"),
                "r-devtools": Package("r-devtools", "r-devtools", "0.1.0", "r351_0"),
            }
        },
    )
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        return_value={
            "trelliscopejs": Package("trelliscopejs", "trelliscopejs" "0.1.0")
        },
    )
    local_packages = HistoryPackages.create(
        Packages((Package.from_spec("r-base"), Package.from_spec("r-devtools")))
    )
    local_packages.update_packages(
        packages=(Package.from_spec("trelliscopejs"),), source="r"
    )
    local_history = History(
        name=ENV_NAME,
        packages=local_packages,
        channels=Channels("defaults"),
        logs=Logs([]),
        actions=Actions(),
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
