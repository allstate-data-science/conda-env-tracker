"""Test main functions."""
# pylint: disable=redefined-outer-name
import shutil

import pytest

from conda_env_tracker.env import Environment
from conda_env_tracker.errors import CondaEnvTrackerPackageNameError
from conda_env_tracker.gateways.io import USER_ENVS_DIR
from conda_env_tracker.history import (
    History,
    HistoryPackages,
    Logs,
    Actions,
    Channels,
    Debug,
)
from conda_env_tracker.main import (
    create,
    diff,
    update_packages,
    sync,
    get_env_name,
    conda_install,
    conda_remove,
    r_install,
    pip_install,
)
from conda_env_tracker.packages import Package, Packages


@pytest.fixture(
    params=[
        {
            "packages": ["pandas"],
            "dependencies": ["pandas=0.22=py36"],
            "local": {"pandas": "0.23=py36"},
            "expected": ["-pandas=0.22=py36", "+pandas=0.23=py36"],
        },
        {
            "packages": ["pandas"],
            "dependencies": ["pandas=0.22=py36"],
            "local": {"pandas": "0.23=py36", "pytest": "0.11=py36"},
            "expected": ["-pandas=0.22=py36", "+pandas=0.23=py36", "+pytest=0.11=py36"],
        },
        {
            "packages": ["python"],
            "dependencies": ["pandas=0.22=py36"],
            "local": {"pandas": "0.23=py36", "pytest": "0.11=py36"},
            "expected": [
                "-python",
                "-pandas=0.22=py36",
                "+pandas=0.23=py36",
                "+pytest=0.11=py36",
            ],
        },
    ]
)
def expected_diff(mocker, request):
    """Set up for diff function"""

    packages = request.param["packages"]
    dependencies = request.param["dependencies"]
    local = request.param["local"]
    name = "test-diff"
    mocker.patch("conda_env_tracker.gateways.io.Path.mkdir")
    mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(return_value={"conda": dependencies, "pip": {}}),
    )
    history = History(
        name=name,
        packages=HistoryPackages.create(packages=packages),
        channels=None,
        logs=None,
        actions=None,
        debug=None,
    )
    env = Environment(name=name, history=history)
    mocker.patch("conda_env_tracker.main.Environment.read", return_value=env)
    mocker.patch(
        "conda_env_tracker.gateways.io.EnvIO.get_environment",
        return_value={
            "name": "test-diff",
            "channels": ["conda-forge"],
            "dependencies": dependencies,
        },
    )
    mocker.patch(
        "conda_env_tracker.history.get_dependencies", return_value={"conda": local}
    )
    yield request.param["expected"]
    if (USER_ENVS_DIR / name).exists():
        shutil.rmtree(USER_ENVS_DIR / name)


@pytest.mark.skip
def test_diff(expected_diff):
    diff_pkges = diff("test-diff")
    assert diff_pkges == expected_diff


@pytest.fixture()
def expected_update(mocker):
    """Set up for update function"""
    packages = Packages.from_specs("pandas")
    channel = "conda-forge"
    create_cmd = "conda install pandas"
    name = "test-update"
    mocker.patch("conda_env_tracker.gateways.io.Path.mkdir")
    mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    mocker.patch("conda_env_tracker.gateways.io.Path.iterdir")
    mocker.patch("conda_env_tracker.history.get_pip_version", return_value=None)
    history = History(
        name=name,
        channels=Channels([channel]),
        packages=HistoryPackages.create(packages),
        logs=Logs.create(create_cmd),
        actions=Actions.create(
            name="test-update", specs=["pandas"], channels=Channels([channel])
        ),
        debug=Debug(),
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={
            "conda": {
                "pandas": Package("pandas", "pandas", "0.23", "py36"),
                "pytest": Package("pytest", "pytest", "0.1", "py36"),
            },
            "pip": {},
        },
    )
    mocker.patch("conda_env_tracker.env.EnvIO.export_packages")
    mocker.patch(
        "conda_env_tracker.main.Environment.read",
        return_value=Environment(name=name, history=history),
    )
    return history


def test_update_add(expected_update):
    update_packages(name="test-update", specs=["pytest"], remove=[])
    history = expected_update
    assert history.packages == {
        "conda": {
            "pandas": Package("pandas", "pandas", "0.23", "py36"),
            "pytest": Package("pytest", "pytest", "0.1", "py36"),
        }
    }
    assert history.logs == [
        "conda install pandas",
        "conda install --name test-update pytest",
    ]
    assert history.actions == [
        "conda create --name test-update pandas "
        "--override-channels --strict-channel-priority "
        "--channel conda-forge",
        "conda install --name test-update pytest=0.1=py36 "
        "--override-channels --strict-channel-priority "
        "--channel conda-forge",
    ]


def test_update_remove(expected_update):
    update_packages(name="test-update", specs=[], remove=["pandas"])
    history = expected_update
    assert history.packages == {"conda": {}}
    assert history.logs == [
        "conda install pandas",
        "conda remove --name test-update pandas",
    ]
    assert history.actions == [
        "conda create --name test-update pandas --override-channels --strict-channel-priority "
        "--channel conda-forge",
        "conda remove --name test-update pandas --override-channels "
        "--channel conda-forge",
    ]


@pytest.mark.parametrize("yes", [True, False])
def test_auto(mocker, yes):
    mocker.patch("conda_env_tracker.gateways.io.Path.mkdir")

    name = "test-auto"
    env = Environment(name=name)
    env_after_pull = Environment(name=name)
    env_after_push = Environment(name=name)

    read_mock = mocker.patch(
        "conda_env_tracker.main.Environment.read", mocker.Mock(return_value=env)
    )
    mocker.patch("conda_env_tracker.main.infer_remote_dir")
    setup_remote_mock = mocker.patch("conda_env_tracker.main.EnvIO.set_remote_dir")
    pull_mock = mocker.patch(
        "conda_env_tracker.main._pull", mocker.Mock(return_value=env_after_pull)
    )
    push_mock = mocker.patch(
        "conda_env_tracker.main._push", mocker.Mock(return_value=env_after_push)
    )

    final_env = sync(name=name, yes=yes)

    read_mock.assert_called()
    setup_remote_mock.assert_not_called()
    pull_mock.assert_called_once_with(env=env, yes=yes)
    push_mock.assert_called_once_with(env=env_after_pull)
    assert final_env == env_after_push


def test_get_name_default(mocker):
    name_mock = mocker.patch("conda_env_tracker.main.get_active_conda_env_name")
    name_mock.configure_mock(return_value="name_of_env")

    name = get_env_name()

    assert name == "name_of_env"
    name_mock.assert_called_once()


def test_get_name_infer(mocker):
    expected_name = "name_of_env"
    remote_dir = "/path/to/git/.conda_env_tracker"

    name_mock = mocker.patch("conda_env_tracker.main.get_active_conda_env_name")
    remote_dir_mock = mocker.patch("conda_env_tracker.main.infer_remote_dir")
    remote_dir_mock.configure_mock(return_value=remote_dir)
    mocker.patch("pathlib.Path.mkdir")
    io_mock = mocker.patch(
        "conda_env_tracker.main.EnvIO.get_history",
        new=mocker.Mock(**{"return_value.name": expected_name}),
    )

    actual_name = get_env_name(infer=True)

    assert actual_name == expected_name
    name_mock.assert_not_called()
    remote_dir_mock.assert_called_once()
    io_mock.assert_called_once()


def test_name_cleaning(mocker):
    create_mock = mocker.patch("conda_env_tracker.main.Environment.create")
    mocker.patch("conda_env_tracker.main.Environment.export")
    mocker.patch("conda_env_tracker.main.jupyter_kernel_install_query")
    mocker.patch(
        "conda_env_tracker.main.prompt_yes_no", mocker.Mock(return_value=False)
    )

    create(name="test", specs=["one", "TWO", "thRee=1.0"])

    create_mock.assert_called_once_with(
        name="test",
        packages=Packages.from_specs(["one", "two", "three=1.0"]),
        channels=None,
        yes=False,
        strict_channel_priority=True,
    )


@pytest.mark.parametrize(
    "package_names, commands",
    [
        (["jsonlite"], ["install.packages('jsonlite')"]),
        (
            ["jsonlite", "testthat"],
            ["install.packages('jsonlite')", "install.packages('testthat')"],
        ),
    ],
)
def test_r_install(mocker, package_names, commands):
    env_mock = mocker.patch("conda_env_tracker.main.Environment.read")
    handler_mock = mocker.patch("conda_env_tracker.main.RHandler.install")
    env_mock.configure_mock(
        **{"return_value.dependencies": {"conda": {"r-base": "3.5.1"}}}
    )
    mocker.patch(
        "conda_env_tracker.main.prompt_yes_no", mocker.Mock(return_value=False)
    )
    name = "test_env_name"
    r_install(name=name, package_names=package_names, commands=commands)
    env_mock.assert_called_once_with(name=name)
    handler_mock.assert_called_once_with(
        packages=[
            Package(package_name, command)
            for package_name, command in zip(package_names, commands)
        ]
    )


def test_r_install_auto_ask_to_sync(mocker):
    env_mock = mocker.patch("conda_env_tracker.main.Environment.read")
    mocker.patch("conda_env_tracker.main.RHandler")
    env_mock.configure_mock(
        **{"return_value.dependencies": {"conda": {"r-base": "3.5.1"}}}
    )
    mocker.patch("conda_env_tracker.main.os.environ", {"CET_AUTO": "0"})
    mocker.patch("conda_env_tracker.main.prompt_yes_no", mocker.Mock(return_value=True))
    mocker.patch(
        "conda_env_tracker.main.EnvIO.is_remote_dir_set", mocker.Mock(return_value=True)
    )
    sync_mock = mocker.patch("conda_env_tracker.main.sync")
    name = "test_env_name"
    r_install(
        name=name, package_names=["testthat"], commands=["install.packages('testthat')"]
    )
    sync_mock.assert_called_once_with(name=name, yes=True)


def test_create_auto_ask_to_sync(mocker):
    mocker.patch("conda_env_tracker.main.os.environ", {"CET_AUTO": "0"})
    mocker.patch("conda_env_tracker.main.prompt_yes_no", mocker.Mock(return_value=True))
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    mocker.patch("conda_env_tracker.main.Environment.create")
    mocker.patch("conda_env_tracker.main.Environment.export")
    mocker.patch("conda_env_tracker.main.jupyter_kernel_install_query")

    name = "test_env_name"

    create(name=name, specs=["python=3.7"])

    sync_mock.assert_not_called()


def test_create_yes_auto_do_not_ask_to_sync(mocker):
    mocker.patch("conda_env_tracker.main.os.environ", {"CET_AUTO": "0"})
    mocker.patch("conda_env_tracker.main.prompt_yes_no", mocker.Mock(return_value=True))
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    mocker.patch("conda_env_tracker.main.Environment.create")
    mocker.patch("conda_env_tracker.main.Environment.export")
    mocker.patch("conda_env_tracker.main.jupyter_kernel_install_query")

    name = "test_env_name"

    create(name=name, specs=["python=3.7"], yes=True)

    sync_mock.assert_not_called()


def test_create_no_auto_do_not_ask_to_sync(mocker):
    mocker.patch("conda_env_tracker.main.os.environ", {})
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    mocker.patch("conda_env_tracker.main.Environment.create")
    mocker.patch("conda_env_tracker.main.Environment.export")
    mocker.patch("conda_env_tracker.main.jupyter_kernel_install_query")

    name = "test_env_name"

    create(name=name, specs=["python=3.7"])

    sync_mock.assert_not_called()


def test_bad_package_name(mocker):
    mocker.patch("conda_env_tracker.main.Environment.read")
    mocker.patch("conda_env_tracker.main.check_pip")

    with pytest.raises(CondaEnvTrackerPackageNameError):
        pip_install(
            name="environment", specs=["git+ssh://git@github.com/pandas-dev/pandas"]
        )


@pytest.mark.parametrize("function", [conda_install, conda_remove, pip_install])
def test_good_package_name(mocker, function):
    mocker.patch("conda_env_tracker.main.Environment.read")
    mocker.patch("conda_env_tracker.main.PipHandler")
    mocker.patch("conda_env_tracker.main.check_pip")
    mocker.patch("conda_env_tracker.main.CondaHandler")

    function(name="environment", specs=["pandas"])
