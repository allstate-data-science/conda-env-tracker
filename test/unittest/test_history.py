"""Test history class functions"""

import pytest
from conda_env_tracker.history import History, Channels, HistoryPackages, Logs, Actions
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.gateways.r import R_COMMAND


def test_parse_without_package():
    """Test to parse yaml file without any package"""
    history = History.parse(
        {
            "channels": None,
            "packages": None,
            "logs": None,
            "actions": None,
            "debug": None,
        }
    )
    assert [] == history.channels
    assert {} == history.packages
    assert [] == history.logs
    assert [] == history.actions
    assert [] == history.debug


def test_parse_with_package():
    """Test to parse yaml file without any package"""
    history = History.parse(
        {
            "channels": ["conda-forge", "main"],
            "packages": {"conda": {"pytest": "*"}},
            "logs": ["conda create --name test pytest"],
            "actions": [
                "conda create --name test pytest=0.1=py36_0 "
                "--channel conda-forge "
                "--channel main"
            ],
            "debug": [{"platform": "linux", "conda_version": "4.5.11"}],
        }
    )
    assert ["conda-forge", "main"] == history.channels
    assert {"conda": {"pytest": Package.from_spec("pytest")}} == history.packages
    assert ["conda create --name test pytest"] == history.logs
    assert [
        "conda create --name test pytest=0.1=py36_0 "
        "--channel conda-forge "
        "--channel main"
    ] == history.actions
    assert [{"platform": "linux", "conda_version": "4.5.11"}] == history.debug


def test_parse_with_package_with_version():
    """Test to parse yaml file without any package"""
    history = History.parse(
        {
            "name": "environment-name",
            "channels": ["conda-forge", "main"],
            "packages": {"conda": {"pytest": "3.7=py36_0"}},
            "logs": ["conda create --name test pytest=3.7=py36_0"],
            "actions": ["conda create --name test pytest=3.7=py36_0"],
            "debug": [{"platform": "osx", "conda_version": "4.5.12"}],
        }
    )
    assert history.name == "environment-name"
    assert history.channels == ["conda-forge", "main"]
    assert history.packages == {
        "conda": {"pytest": Package.from_spec("pytest=3.7=py36_0")}
    }
    assert history.logs == ["conda create --name test pytest=3.7=py36_0"]
    assert history.actions == ["conda create --name test pytest=3.7=py36_0"]
    assert history.debug == [{"platform": "osx", "conda_version": "4.5.12"}]


def test_export_success():
    """Test package export"""
    expected = {
        "name": "environment-name",
        "channels": ["conda-forge", "main"],
        "packages": {"conda": {"pytest": "*"}},
        "logs": ["conda create --name test pytest"],
        "actions": [
            "conda create --name test pytest=0.1=py36_0 "
            "--channel conda-forge "
            "--channel main"
        ],
        "debug": [{"platform": "osx", "conda_version": "4.5.10"}],
    }
    actual = History(
        name="environment-name",
        channels=Channels(["conda-forge", "main"]),
        packages=HistoryPackages(conda=dict(pytest=Package.from_spec("pytest"))),
        logs=Logs(["conda create --name test pytest"]),
        actions=Actions(
            [
                "conda create --name test pytest=0.1=py36_0 "
                "--channel conda-forge "
                "--channel main"
            ]
        ),
        debug=[{"platform": "osx", "conda_version": "4.5.10"}],
    ).export()
    assert expected == actual


def test_export_empty():
    """Test package export"""
    expected = {
        "name": "",
        "channels": [],
        "packages": {},
        "logs": [],
        "actions": [],
        "debug": [],
    }
    actual = History(
        name="",
        channels=Channels(channels=[]),
        packages=HistoryPackages(),
        logs=Logs(),
        actions=Actions([]),
        debug=[],
    ).export()
    assert expected == actual


def test_ignore_empty_pip_packages():
    """When a user installs a pip package and then removes it, the pip packages is an empty dictionry which
    does not need to show up in the history file.
    """
    expected = {
        "name": "environment-name",
        "channels": ["main"],
        "packages": {"conda": {"pytest": "*"}},
        "logs": ["conda create --name test pytest"],
        "actions": ["conda create --name test pytest=0.1=py36_0 " "--channel main"],
        "debug": [{"platform": "osx", "conda_version": "4.5.10"}],
    }
    actual = History(
        name="environment-name",
        channels=Channels(["main"]),
        packages=HistoryPackages(
            conda=dict(pytest=Package.from_spec("pytest")), pip={}
        ),
        logs=Logs(["conda create --name test pytest"]),
        actions=Actions(
            ["conda create --name test pytest=0.1=py36_0 " "--channel main"]
        ),
        debug=[{"platform": "osx", "conda_version": "4.5.10"}],
    ).export()
    assert expected == actual


def test_get_create_action():
    """Test create action string"""
    channels = Channels(["conda-forge", "main"])
    expected = [
        (
            "conda create --name test-create python=3.6.6=py_36 pandas=0.23.1=py_36 "
            "--override-channels --strict-channel-priority "
            "--channel conda-forge "
            "--channel main"
        )
    ]
    actual = Actions.create(
        "test-create", ["python=3.6.6=py_36", "pandas=0.23.1=py_36"], channels=channels
    )
    assert expected == actual


@pytest.mark.parametrize(
    "spec",
    [
        "numpy=0.1=py36_1",
        "pytest=0.26=py37_3",
        "num-py=0.1=hbdcb_4",
        "num987-py=0.1=py36_2",
        "num987-py=0.1=hfc3654",
    ],
)
def test_extract_packages_from_actions(spec):
    """Test parsing the packges from action item"""
    action = Actions.create(
        name="test-extract",
        specs=[spec],
        channels=Channels(["conda-forge", "conda-remote"]),
    )
    packages = action.extract_packages(index=0)

    assert packages[0] == Package.from_spec(spec)


@pytest.mark.parametrize("spec", ["numpy", "pytest=0.26", "num-py=0.1=hbdcb_4"])
def test_extract_packages_from_logs(spec):
    """Test parsing the packges from action item"""
    log = Logs.create(command=f"conda install --name test {spec}")
    packages = log.extract_packages(index=0, packages=Packages.from_specs(spec))

    assert packages[0] == Package.from_spec(spec)


@pytest.mark.parametrize(
    "log, expected",
    [
        ("conda remove --name test python", Packages.from_specs("python")),
        (
            "conda remove --name test2 python pandas",
            Packages.from_specs(["python", "pandas"]),
        ),
        ("pip uninstall pandas", Packages.from_specs("pandas")),
        ("pip uninstall pandas numpy", Packages.from_specs(["pandas", "numpy"])),
        (
            f"{R_COMMAND} -e 'remove.packages(c(\"dplyr\"))'",
            Packages.from_specs("dplyr"),
        ),
        (
            f'{R_COMMAND} -e \'remove.packages(c("dplyr","testthat"))\'',
            Packages.from_specs(["dplyr", "testthat"]),
        ),
    ],
)
def test_extract_removed_packages_from_logs(log, expected):
    logs = Logs.create(command=f"conda create --name test python=3.7")
    logs.append(log)
    actual = logs.extra_removed_packages(index=1)
    assert actual == expected
