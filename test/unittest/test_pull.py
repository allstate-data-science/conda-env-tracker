"""Test cases for conda_env_tracker pull from remote"""
# pylint: disable=redefined-outer-name
import copy
import shutil

import pytest

from conda_env_tracker.env import Environment
from conda_env_tracker.errors import CondaEnvTrackerCreationError
from conda_env_tracker.gateways.io import USER_ENVS_DIR
from conda_env_tracker.gateways.r import R_COMMAND
from conda_env_tracker.history import (
    History,
    HistoryPackages,
    Logs,
    Channels,
    Actions,
    Debug,
)
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.pull import pull

ENV_NAME = "pull_testing_environment"
CHANNELS = Channels(["conda-forge", "main"])


@pytest.fixture(scope="function")
def setup_tests(mocker):
    """Set up for pull function"""
    remote_packages = (Package.from_spec("pandas"), Package.from_spec("pytest"))
    remote_logs = [
        "conda create --name pull_testing_environment pandas",
        "conda install --name pull_testing_environment pytest",
    ]
    remote_actions = [
        "conda create --name pull_testing_environment pandas=0.23=py36",
        "conda install --name pull_testing_environment pytest=0.1=py36_3",
    ]
    remote_history = History(
        name=ENV_NAME,
        channels=CHANNELS,
        packages=HistoryPackages.create(remote_packages),
        logs=Logs([log for log in remote_logs]),
        actions=Actions(remote_actions),
        debug=Debug(),
    )

    mocker.patch("conda_env_tracker.conda.conda_install")
    mocker.patch("conda_env_tracker.conda.conda_update_all")
    mocker.patch("conda_env_tracker.conda.conda_remove")
    mocker.patch("conda_env_tracker.pip.pip_install")
    mocker.patch("conda_env_tracker.pip.pip_remove")
    mocker.patch("conda_env_tracker.history.get_pip_version")
    get_dependencies = mocker.patch("conda_env_tracker.env.get_dependencies")

    overwrite_mock = mocker.patch("conda_env_tracker.pull.EnvIO.overwrite_local")
    mocker.patch(
        "conda_env_tracker.pull.EnvIO.get_remote_dir", return_value="~/path/to/remote"
    )
    mocker.patch(
        "conda_env_tracker.pull.EnvIO.get_history", return_value=remote_history
    )
    mocker.patch("conda_env_tracker.pull.prompt_yes_no", return_value=True)
    mocker.patch("conda_env_tracker.pull.update_conda_environment")
    mocker.patch("conda_env_tracker.pull.update_r_environment")
    mocker.patch("conda_env_tracker.pull.Environment.export")
    mocker.patch("conda_env_tracker.pull.Environment.validate")
    mocker.patch("conda_env_tracker.pull.Environment.validate_installed_packages")

    yield {
        "get_dependencies": get_dependencies,
        "overwrite_mock": overwrite_mock,
        "remote_history": remote_history,
    }

    env_dir = USER_ENVS_DIR / ENV_NAME
    if env_dir.exists():
        shutil.rmtree(env_dir)


@pytest.fixture(scope="function")
def setup_r_tests(mocker):
    """Set up for pull function with R packages"""
    remote_packages = Packages.from_specs("r-base")
    remote_logs = ["conda create --name pull_testing_environment r-base"]
    remote_actions = ["conda create --name pull_testing_environment r-base=3.5.1=h351"]
    remote_history = History(
        name=ENV_NAME,
        channels=CHANNELS,
        packages=HistoryPackages.create(remote_packages),
        logs=Logs([log for log in remote_logs]),
        actions=Actions(remote_actions),
        debug=Debug(),
    )

    mocker.patch("conda_env_tracker.conda.conda_install")
    mocker.patch("conda_env_tracker.pip.pip_install")
    mocker.patch("conda_env_tracker.history.get_pip_version")

    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False})

    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        return_value={"conda": {"r-base": "3.5.1"}},
    )
    get_r_dependencies = mocker.patch("conda_env_tracker.env.get_r_dependencies")
    overwrite_mock = mocker.patch("conda_env_tracker.pull.EnvIO.overwrite_local")
    mocker.patch(
        "conda_env_tracker.pull.EnvIO.get_remote_dir", return_value="~/path/to/remote"
    )
    mocker.patch(
        "conda_env_tracker.pull.EnvIO.get_history", return_value=remote_history
    )
    mocker.patch("conda_env_tracker.pull.prompt_yes_no", return_value=True)
    mocker.patch("conda_env_tracker.pull.update_conda_environment")
    mocker.patch("conda_env_tracker.pull.update_r_environment")
    mocker.patch("conda_env_tracker.pull.Environment.export")
    mocker.patch("conda_env_tracker.pull.Environment.validate")

    yield {
        "get_r_dependencies": get_r_dependencies,
        "overwrite_mock": overwrite_mock,
        "remote_history": remote_history,
    }

    env_dir = USER_ENVS_DIR / ENV_NAME
    if env_dir.exists():
        shutil.rmtree(env_dir)


@pytest.mark.parametrize(
    "local_packages, local_logs, local_actions",
    (
        (
            (Package.from_spec("pandas"), Package.from_spec("pytest")),
            [
                "conda create --name pull_testing_environment pandas",
                "conda install --name pull_testing_environment pytest",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                "conda install --name pull_testing_environment pytest=0.1=py36_3",
            ],
        ),
        (
            (
                Package.from_spec("pandas"),
                Package.from_spec("pytest"),
                Package.from_spec("pylint"),
            ),
            [
                "conda create --name pull_testing_environment pandas",
                "conda install --name pull_testing_environment pytest",
                "conda install --name pull_testing_environment pylint",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                "conda install --name pull_testing_environment pytest=0.1=py36_3",
                "conda install --name pull_testing_environment pylint=0.2=py36_3",
            ],
        ),
    ),
)
def test_pull_no_new_action_in_remote(
    setup_tests, local_packages, local_logs, local_actions
):
    overwrite_mock = setup_tests["overwrite_mock"]

    local_history = History(
        name=ENV_NAME,
        packages=HistoryPackages.create(local_packages),
        channels=Channels(),
        logs=Logs([log for log in local_logs]),
        actions=Actions(local_actions),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    pull(env=env)

    assert env.history.packages == local_history.packages
    assert env.history.logs == local_history.logs
    assert env.history.actions == local_history.actions
    overwrite_mock.assert_not_called()


def test_pull_no_new_action_in_local(setup_tests):
    overwrite_mock = setup_tests["overwrite_mock"]
    remote_history = setup_tests["remote_history"]

    local_packages = (Package.from_spec("pandas"),)
    local_logs = ["conda create --name pull_testing_environment pandas"]
    local_actions = ["conda create --name pull_testing_environment pandas=0.23=py36"]

    local_history = History(
        name=ENV_NAME,
        packages=HistoryPackages.create(local_packages),
        channels=Channels(),
        logs=Logs([log for log in local_logs]),
        actions=Actions(local_actions),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    pull(env=env)

    assert env.history.packages == remote_history.packages
    assert env.history.logs == remote_history.logs
    assert env.history.actions == remote_history.actions
    overwrite_mock.called_once()


def test_pull_actions_in_different_order(setup_tests):
    overwrite_mock = setup_tests["overwrite_mock"]
    remote_history = setup_tests["remote_history"]

    new_log = "conda install --name pull_testing_environment pylint"
    new_action = "conda install --name pull_testing_environment pylint=1.11=py36"

    remote_history.packages["pylint"] = "*"
    remote_history.logs.append(new_log)
    remote_history.actions.append(new_action)

    local_packages = (
        Package.from_spec("pandas"),
        Package.from_spec("pylint"),
        Package.from_spec("pytest"),
    )
    local_logs = [
        "conda create --name pull_testing_environment pandas",
        new_log,
        "conda install --name pull_testing_environment pytest",
    ]
    local_actions = [
        "conda create --name pull_testing_environment pandas=0.23=py36",
        new_action,
        "conda install --name pull_testing_environment pytest=0.1=py36_3",
    ]
    local_history = History(
        name=ENV_NAME,
        channels=CHANNELS,
        packages=HistoryPackages.create(local_packages),
        logs=Logs([log for log in local_logs]),
        actions=Actions(local_actions),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    pull(env=env)

    assert env.history.packages == remote_history.packages
    assert env.history.logs == remote_history.logs
    assert env.history.actions == remote_history.actions
    overwrite_mock.called_once()


@pytest.mark.parametrize(
    "local_packages, local_logs, local_actions",
    (
        pytest.param(
            {"conda": (Package.from_spec("pandas"), Package.from_spec("pylint"))},
            [
                "conda create --name pull_testing_environment pandas",
                "conda install --name pull_testing_environment pylint",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda install --name pull_testing_environment pylint=1.11=py36 "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
            id="Installed another package",
        ),
        pytest.param(
            {
                "conda": (
                    Package.from_spec("pandas"),
                    Package.from_spec("pylint=1.11=py36"),
                )
            },
            [
                "conda create --name pull_testing_environment pandas",
                "conda install --name pull_testing_environment pylint=1.11=py36",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda install --name pull_testing_environment pylint=1.11=py36 "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
            id="Installed another package with specific spec",
        ),
        pytest.param(
            {
                "conda": (Package.from_spec("pandas"),),
                "pip": (Package.from_spec("pylint"),),
            },
            [
                "conda create --name pull_testing_environment pandas",
                "pip install pylint --index-url https://pypi.org/simple",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                "pip install pylint==1.11 --index-url https://pypi.org/simple",
            ],
            id="Pip installed another package",
        ),
        pytest.param(
            {"conda": tuple()},
            [
                "conda create --name pull_testing_environment pandas",
                "conda remove --name pull_testing_environment pandas",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda remove --name pull_testing_environment pandas --override-channels "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
            id="Conda remove package",
        ),
        pytest.param(
            {"conda": (Package.from_spec("pandas"),), "pip": tuple()},
            [
                "conda create --name pull_testing_environment pandas",
                "pip install pylint --index-url https://pypi.org/simple",
                "pip uninstall pylint",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                "pip install pylint==1.11 --index-url https://pypi.org/simple",
                "pip uninstall pylint",
            ],
            id="Pip remove package",
        ),
        pytest.param(
            {"conda": (Package.from_spec("pandas"),)},
            [
                "conda create --name pull_testing_environment pandas",
                "conda update --all --name pull_testing_environment",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda update --all --name pull_testing_environment "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
            id="Conda update --all",
        ),
        pytest.param(
            {"conda": (Package.from_spec("pandas"), Package.from_spec("pylint"))},
            [
                "conda create --name pull_testing_environment pandas",
                "conda update --all pylint --name pull_testing_environment",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda update --all --name pull_testing_environment pylint=1.11=py36 "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
            id="Conda update --all with new package",
        ),
    ),
)
def test_pull_new_action_in_both(
    setup_tests, local_packages, local_logs, local_actions
):
    overwrite_mock = setup_tests["overwrite_mock"]
    remote_history = setup_tests["remote_history"]
    packages_mock = setup_tests["get_dependencies"]

    packages = HistoryPackages.create(local_packages["conda"])
    if local_packages.get("pip"):
        packages.update_packages(local_packages["pip"], source="pip")

    local_history = History(
        name=ENV_NAME,
        channels=CHANNELS,
        packages=packages,
        logs=Logs([log for log in local_logs]),
        actions=Actions(local_actions),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    if local_packages.get("pip") is not None:
        packages_mock.configure_mock(
            return_value={
                "conda": {
                    "pandas": Package("pandas", "pandas", "0.23", "py36"),
                    "pytest": Package("pytest", "pytest", "0.1", "py36_3"),
                },
                "pip": {"pylint": Package("pylint", "pylint", "1.11")},
            }
        )
    else:
        packages_mock.configure_mock(
            return_value={
                "conda": {
                    "pandas": Package("pandas", "pandas", "0.23", "py36"),
                    "pytest": Package("pytest", "pytest", "0.1", "py36_3"),
                    "pylint": Package("pylint", "pylint", "1.11", "py36"),
                },
                "pip": {},
            }
        )

    pull(env=env)

    expected_packages = remote_history.packages
    if local_packages.get("pip"):
        expected_packages["pip"]["pylint"] = local_history.packages["pip"]["pylint"]
    elif "pylint" in local_history.packages["conda"]:
        expected_packages["conda"]["pylint"] = local_history.packages["conda"]["pylint"]
    expected_logs = remote_history.logs
    expected_actions = remote_history.actions

    assert env.history.packages == expected_packages
    assert env.history.logs == expected_logs
    assert env.history.actions == expected_actions
    assert env.history.logs[-1] == local_history.logs[-1]
    assert env.history.actions[-1] == local_history.actions[-1]
    overwrite_mock.called_once()


@pytest.mark.parametrize(
    "local_packages, local_logs, local_actions",
    (
        (
            (Package.from_spec("pandas=0.23=py36"), Package.from_spec("pylint")),
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                "conda install --name pull_testing_environment pylint",
            ],
            [
                "conda create --name pull_testing_environment pandas=0.23=py36",
                (
                    "conda install --name pull_testing_environment pylint=1.11=py36 "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
        ),
        (
            (Package.from_spec("numpy"), Package.from_spec("pylint")),
            [
                "conda create --name pull_testing_environment numpy",
                "conda install --name pull_testing_environment pylint",
            ],
            [
                "conda create --name pull_testing_environment numpy=1.12=py36",
                (
                    "conda install --name pull_testing_environment pylint=1.11=py36 "
                    "--override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ),
            ],
        ),
    ),
)
def test_pull_remote_local_different_create_commands(
    setup_tests, local_packages, local_logs, local_actions
):
    # pylint: disable=unused-argument
    local_history = History(
        name=ENV_NAME,
        channels=CHANNELS,
        packages=HistoryPackages.create(local_packages),
        logs=Logs([log for log in local_logs]),
        actions=Actions(local_actions),
        debug=Debug(),
    )
    env = Environment(name=ENV_NAME, history=local_history)

    with pytest.raises(CondaEnvTrackerCreationError):
        pull(env=env)


def test_empty_local_history(setup_tests):
    """Empty local history should pull successfully."""
    env = Environment(name="test", history=None)
    final_env = pull(env=env)
    assert final_env.history == setup_tests["remote_history"]
    setup_tests["overwrite_mock"].assert_called_once()


def test_pull_pip(setup_tests):
    new = Package.from_spec("pytest-pylint==0.13.0")
    remote_history = setup_tests["remote_history"]

    remote_history.packages.update_packages(packages=[new], source="pip")
    remote_history.logs.append(f"pip install {new}")
    remote_history.actions.append(f"pip install {new}")

    env = Environment(name="test", history=None)
    final_env = pull(env=env)

    assert final_env.history == remote_history


def test_pull_different_actions_with_pip(setup_tests):
    new = Package.from_spec("pytest-pylint==0.13.0")
    remote_history = setup_tests["remote_history"]

    local_history = copy.deepcopy(remote_history)
    env = Environment(name=local_history.name, history=local_history)

    remote_history.packages.update_packages(packages=[new], source="pip")
    remote_history.logs.append(f"pip install {new}")
    remote_history.actions.append(f"pip install {new}")

    final_env = pull(env=env)

    assert final_env.history == remote_history


def test_pull_r(setup_r_tests):
    remote_history = setup_r_tests["remote_history"]

    remote_history.packages.update_packages(
        packages=Packages(Package("jsonlite", "install.packages('jsonlite')")),
        source="r",
    )
    remote_history.logs.append(f"{R_COMMAND} -e 'install.packages('jsonlite')'")
    remote_history.actions.append(f"{R_COMMAND} -e 'install.packages('jsonlite')'")

    env = Environment(name="test", history=None)
    final_env = pull(env=env)

    assert final_env.history == remote_history


def test_pull_different_actions_in_both_r(setup_r_tests):
    remote_history = setup_r_tests["remote_history"]
    get_r_dependencies = setup_r_tests["get_r_dependencies"]
    get_r_dependencies.configure_mock(
        **{
            "return_value": {
                "praise": Package("praise", "praise", "1.0.0"),
                "jsonlite": Package("jsonlite", "jsonlite", "1.6"),
            }
        }
    )

    local_history = copy.deepcopy(remote_history)

    local_history.packages.update_packages(
        packages=Packages(Package("praise", 'install.packages("praise")')), source="r"
    )
    local_history.logs.append(f"{R_COMMAND} -e 'install.packages(\"praise\")'")
    local_history.actions.append(f"{R_COMMAND} -e 'install.packages(\"praise\")'")

    env = Environment(name=local_history.name, history=local_history)

    remote_history.packages.update_packages(
        packages=Packages(Package("jsonlite", 'install.packages("jsonlite")')),
        source="r",
    )
    remote_history.logs.append(f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'")
    remote_history.actions.append(f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'")

    expected_history = copy.deepcopy(remote_history)

    expected_history.packages.update_packages(
        packages=Packages(Package("praise", 'install.packages("praise")')), source="r"
    )
    expected_history.logs.append(f"{R_COMMAND} -e 'install.packages(\"praise\")'")
    expected_history.actions.append(f"{R_COMMAND} -e 'install.packages(\"praise\")'")

    final_env = pull(env=env)

    assert final_env.history.packages == expected_history.packages
    assert final_env.history.logs == expected_history.logs
    assert final_env.history.actions == expected_history.actions


@pytest.mark.parametrize("remove_location", ["remote", "local"])
def test_pull_different_actions_in_both_remove_package_r(
    setup_r_tests, remove_location
):
    remote_history = setup_r_tests["remote_history"]
    get_r_dependencies = setup_r_tests["get_r_dependencies"]
    get_r_dependencies.configure_mock(
        **{
            "return_value": {
                "praise": Package("praise", "praise", "1.0.0"),
                "jsonlite": Package("jsonlite", "jsonlite", "1.6"),
            }
        }
    )

    def update_histories(history_1, history_2):
        add_log_1 = f"{R_COMMAND} -e 'install.packages(\"praise\")'"
        remove_log_1 = f"{R_COMMAND} -e 'remove.packages(c(\"praise\"))'"

        history_1.logs.append(add_log_1)
        history_1.logs.append(remove_log_1)
        history_1.actions.append(add_log_1)
        history_1.actions.append(remove_log_1)

        packages_2 = Packages(Package("jsonlite", 'install.packages("jsonlite")'))
        log_2 = f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'"
        action_2 = f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'"
        history_2.packages.update_packages(packages=packages_2, source="r")
        history_2.logs.append(log_2)
        history_2.actions.append(action_2)
        return history_1, history_2

    local_history = copy.deepcopy(remote_history)

    if remove_location == "local":
        local_history, remote_history = update_histories(local_history, remote_history)
    else:
        remote_history, local_history = update_histories(remote_history, local_history)

    env = Environment(name=local_history.name, history=local_history)

    expected_history = copy.deepcopy(remote_history)

    for index, log in enumerate(local_history.logs):
        if log not in remote_history.logs:
            expected_history.logs.append(log)
            expected_history.actions.append(local_history.actions[index])

    expected_history.packages["r"] = {
        "jsonlite": Package("jsonlite", 'install.packages("jsonlite")')
    }

    final_env = pull(env=env)

    final_env.history.debug = []

    if remove_location == "local":
        # If user added and removed packages, then we do not add both logs
        expected_history.logs.pop(2)
        expected_history.actions.pop(2)

    assert final_env.history.packages == expected_history.packages
    assert final_env.history.logs == expected_history.logs
    assert final_env.history.actions == expected_history.actions


@pytest.mark.parametrize("remove_location", ["remote", "local"])
def test_pull_different_actions_in_both_remove_multiple_packages_r(
    setup_r_tests, remove_location
):
    remote_history = setup_r_tests["remote_history"]
    get_r_dependencies = setup_r_tests["get_r_dependencies"]
    get_r_dependencies.configure_mock(
        **{
            "return_value": {
                "praise": Package("praise", "praise", "1.0.0"),
                "dplyr": Package("dplyr", "dplyr", "0.8.3"),
                "jsonlite": Package("jsonlite", "jsonlite", "1.6"),
            }
        }
    )

    def update_histories(history_1, history_2):
        add_log_1 = (
            f'{R_COMMAND} -e \'install.packages("praise");install.packages("dplyr")\''
        )
        remove_log_1 = f'{R_COMMAND} -e \'remove.packages(c("praise","dplyr"))\''

        history_1.logs.append(add_log_1)
        history_1.logs.append(remove_log_1)
        history_1.actions.append(add_log_1)
        history_1.actions.append(remove_log_1)

        packages_2 = Packages(Package("jsonlite", 'install.packages("jsonlite")'))
        log_2 = f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'"
        action_2 = f"{R_COMMAND} -e 'install.packages(\"jsonlite\")'"
        history_2.packages.update_packages(packages=packages_2, source="r")
        history_2.logs.append(log_2)
        history_2.actions.append(action_2)
        return history_1, history_2

    local_history = copy.deepcopy(remote_history)

    if remove_location == "local":
        local_history, remote_history = update_histories(local_history, remote_history)
    else:
        remote_history, local_history = update_histories(remote_history, local_history)

    env = Environment(name=local_history.name, history=local_history)

    expected_history = copy.deepcopy(remote_history)

    for index, log in enumerate(local_history.logs):
        if log not in remote_history.logs:
            expected_history.logs.append(log)
            expected_history.actions.append(local_history.actions[index])

    expected_history.packages["r"] = {
        "jsonlite": Package("jsonlite", 'install.packages("jsonlite")')
    }

    final_env = pull(env=env)

    final_env.history.debug = []

    if remove_location == "local":
        # If user added and removed packages, then we do not add both logs
        expected_history.logs.pop(2)
        expected_history.actions.pop(2)

    assert final_env.history.packages == expected_history.packages
    assert final_env.history.logs == expected_history.logs
    assert final_env.history.actions == expected_history.actions
