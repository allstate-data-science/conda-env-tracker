"""Test the CondaHandler functionality."""
import copy

import pytest

from conda_env_tracker.conda import CondaHandler
from conda_env_tracker.packages import Package, Packages


@pytest.mark.parametrize("channels", (["conda-forge"], ["pro"], ["pro", "conda-forge"]))
def test_package_install_with_custom_channel(setup_env, channels, mocker):
    """The user can specify a list of channels that will override the channel precedence order or
    they can specify a custom channel that is not previously in the environment's channel list"""
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                "pyspark": Package("pyspark", "pyspark", "0.21", "py_36"),
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_install")

    CondaHandler(env=env).install(
        packages=Packages.from_specs("pyspark"), channels=channels
    )

    history = env_io.get_history()

    expected_log = expected["logs"].copy()
    expected_action = expected["actions"].copy()
    expected_packages = copy.deepcopy(expected["packages"])

    expected_packages["conda"]["pyspark"] = Package.from_spec("pyspark")
    channel_log_string = " ".join(["--channel " + channel for channel in channels])
    expected_log.append(f"conda install --name {env.name} pyspark {channel_log_string}")

    computed_channels = channels.copy()
    for channel in expected["channels"]:
        if not channel in computed_channels:
            computed_channels.append(channel)

    install_channel_string = (
        "--override-channels --strict-channel-priority "
        + " ".join([f"--channel " + channel for channel in computed_channels])
    )

    assert history.packages == expected_packages
    expected_action.append(
        f"conda install --name {env.name} pyspark=0.21=py_36 {install_channel_string}"
    )
    assert history.actions == expected_action
    assert history.logs == expected_log


@pytest.mark.parametrize(
    "packages",
    (Packages.from_specs("pyspark"), Packages.from_specs("pyspark=0.21=py_36")),
)
def test_install_with_default_version_success(setup_env, packages, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                "pyspark": Package("pyspark", "pyspark", "0.21", "py_36"),
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_install")

    CondaHandler(env=env).install(packages=packages)

    history = env_io.get_history()

    expected_log = expected["logs"].copy()
    expected_action = expected["actions"].copy()
    expected_packages = copy.deepcopy(expected["packages"])
    package = packages[0]
    expected_packages["conda"]["pyspark"] = package
    expected_log.append(f"conda install --name {env.name} {package.spec}")

    assert history.packages == expected_packages
    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    expected_action.append(
        f"conda install --name {env.name} pyspark=0.21=py_36 {channel_string}"
    )
    assert history.actions == expected_action
    assert history.logs == expected_log


def test_install_with_default_version_and_yes_success(setup_env, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]
    initial_conda_packages = setup_env["initial_conda_packages"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                **initial_conda_packages,
                "pyspark": Package("pyspark", "pyspark", "0.21", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_install")

    packages = Packages.from_specs("pyspark")
    CondaHandler(env=env).install(packages=packages)

    history = env_io.get_history()

    expected_log = expected["logs"].copy()
    expected_action = expected["actions"].copy()
    expected_packages = copy.deepcopy(expected["packages"])

    expected_packages["conda"]["pyspark"] = Package.from_spec("pyspark")
    expected_log.append(f"conda install --name {env.name} pyspark")

    assert history.packages == expected_packages
    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    expected_action.append(
        f"conda install --name {env.name} pyspark=0.21=py_36 {channel_string}"
    )
    assert history.actions == expected_action
    assert history.logs == expected_log


@pytest.mark.parametrize(
    "packages",
    (
        Packages.from_specs("numpy>1.10"),
        Packages.from_specs("numpy=1.11.1|1.11.3"),
        Packages.from_specs("numpy>=1.10,<1.12"),
    ),
)
def test_install_with_special_bash_char(setup_env, packages, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                "numpy": Package("numpy", "numpy", "1.11.1", "py_36"),
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_install")

    CondaHandler(env=env).install(packages=packages)

    history = env_io.get_history()

    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )

    expected_log = expected["logs"].copy()

    expected_action = expected["actions"].copy()

    expected_packages = copy.deepcopy(expected["packages"])

    package = packages[0]
    expected_packages["conda"]["numpy"] = packages[0]
    expected_log.append(f'conda install --name {env.name} "{package.spec}"')
    expected_action.append(
        f"conda install --name {env.name} numpy=1.11.1=py_36 {channel_string}"
    )

    assert history.packages == expected_packages
    assert history.actions == expected_action
    assert history.logs == expected_log


def test_install_unexpectedly_removes_package(setup_env, mocker):
    """Simulating that installing python=3.8 uninstalls pandas and
    there is no version of pandas available for python 3.8
    """
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]
    logger_mock = mocker.patch("conda_env_tracker.env.logger.warning")

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.return_value = {
        "conda": {"python": Package("python", "python", "3.8", "py_38")}
    }

    mocker.patch("conda_env_tracker.conda.conda_install")

    CondaHandler(env=env).install(packages=Packages.from_specs("python=3.8"))

    history = env_io.get_history()

    expected_packages = {"conda": {"python": Package.from_spec("python=3.8")}}

    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    expected_log = expected["logs"].copy()
    expected_log.append(f"conda install --name {env.name} python=3.8")

    expected_action = expected["actions"].copy()
    expected_action.append(
        f"conda install --name {env.name} python=3.8=py_38 {channel_string}"
    )

    assert history.packages == expected_packages
    assert history.logs == expected_log
    assert history.actions == expected_action
    logger_mock.assert_called_once_with(
        'Package "pandas" was removed during the last command.'
    )


def test_update_all_no_packages(setup_env, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]
    expected_packages = copy.deepcopy(expected["packages"])

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={"conda": {"pandas": Package("pandas", "pandas", "0.24", "py_36")}}
    )

    mocker.patch("conda_env_tracker.conda.conda_update_all")

    CondaHandler(env=env).update_all()

    history = env_io.get_history()

    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    expected_log = expected["logs"].copy()
    expected_log.append(f"conda update --all --name {env.name}")

    expected_action = expected["actions"].copy()
    expected_action.append(f"conda update --all --name {env.name} {channel_string}")

    expected_packages["conda"] = {
        k: Package(v.name, v.name) for k, v in expected_packages["conda"].items()
    }

    assert history.packages == expected_packages
    assert history.logs == expected_log
    assert history.actions == expected_action


@pytest.mark.parametrize(
    "package", [Package.from_spec("pandas"), Package.from_spec("pandas=0.24")]
)
def test_update_all(setup_env, package, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={"conda": {"pandas": Package("pandas", "pandas", "0.24", "py_36")}}
    )

    mocker.patch("conda_env_tracker.conda.conda_update_all")

    packages = Packages(package)
    CondaHandler(env=env).update_all(packages=packages)

    history = env_io.get_history()

    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    expected_log = expected["logs"].copy()

    expected_log.append(f"conda update --all --name {env.name} {package.spec}")

    action_packages_cmd = " pandas=0.24=py_36"

    expected_action = expected["actions"].copy()
    expected_action.append(
        f"conda update --all --name {env.name}{action_packages_cmd} {channel_string}"
    )

    expected_packages = {
        "conda": {"pandas": Package("pandas", package.spec, "0.24", "py_36")}
    }

    assert history.packages == expected_packages
    assert history.logs == expected_log
    assert history.actions == expected_action


def test_remove_package(setup_env, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    mocker.patch("conda_env_tracker.conda.conda_remove")

    packages = Packages.from_specs("pandas")
    CondaHandler(env=env).remove(packages=packages)

    history = env_io.get_history()
    assert history.channels == expected["channels"]
    assert history.packages == {}
    assert history.logs == expected["logs"] + [f"conda remove --name {env.name} pandas"]
    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    remove_channel_string = channel_string.replace("--strict-channel-priority ", "")
    assert history.actions == expected["actions"] + [
        f"conda remove --name {env.name} pandas {remove_channel_string}"
    ]


def test_remove_dependency(setup_env, mocker):
    """Test removing a dependency 'numpy' which will cause the package 'pandas' to be removed."""
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]
    logger_mock = mocker.patch("conda_env_tracker.env.logger.warning")

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={"conda": {"numpy": Package("numpy", "numpy", "1.1", "py_36")}}
    )
    env.dependencies["conda"]["numpy"] = "1.1=py_36"

    mocker.patch("conda_env_tracker.conda.conda_remove")

    packages = Packages.from_specs("numpy")
    CondaHandler(env=env).remove(packages=packages)

    history = env_io.get_history()

    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        [f"--channel " + channel for channel in expected["channels"]]
    )
    remove_channel_string = channel_string.replace("--strict-channel-priority ", "")
    expected_log = expected["logs"].copy()
    expected_log.append(f"conda remove --name {env.name} numpy")

    expected_action = expected["actions"].copy()
    expected_action.append(
        f"conda remove --name {env.name} numpy {remove_channel_string}"
    )

    expected_packages = {}
    assert history.packages == expected_packages
    assert history.logs == expected_log
    assert history.actions == expected_action
    logger_mock.assert_called_once_with(
        'Package "pandas" was removed during the last command.'
    )


@pytest.mark.parametrize("channels", (["conda-forge"], ["pro"], ["pro", "conda-forge"]))
def test_remove_custom_channels(setup_env, channels, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    mocker.patch("conda_env_tracker.conda.conda_remove")

    packages = Packages.from_specs("pandas")
    CondaHandler(env=env).remove(packages=packages, channels=channels)

    history = env_io.get_history()
    assert history.channels == expected["channels"]
    assert history.packages == {}
    assert history.logs == expected["logs"] + [
        f"conda remove --name {env.name} pandas "
        + " ".join(["--channel " + channel for channel in channels])
    ]

    computed_channels = channels.copy()
    for channel in expected["channels"]:
        if channel not in computed_channels:
            computed_channels.append(channel)

    remove_channel_string = "--override-channels " + " ".join(
        [f"--channel " + channel for channel in computed_channels]
    )

    assert history.actions == expected["actions"] + [
        f"conda remove --name {env.name} pandas {remove_channel_string}"
    ]


def test_update_history_conda_remove(setup_env):
    env = setup_env["env"]
    expected = setup_env["expected"]
    channels = expected["channels"]

    packages = Packages.from_specs("pandas")
    CondaHandler(env=env).update_history_remove(packages=packages)

    history = env.history

    log = f"conda remove --name {env.name} pandas"
    action = f"conda remove --name {env.name} pandas --override-channels " + " ".join(
        "--channel " + channel for channel in channels
    )
    expected_logs = expected["logs"].copy()
    expected_actions = expected["actions"].copy()
    expected_logs.append(log)
    expected_actions.append(action)

    assert history.logs == expected_logs
    assert history.actions == expected_actions


def test_strict_channel_priority_install(setup_env, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                "pyspark": Package("pyspark", "pyspark", "0.21", "py_36"),
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_install")

    CondaHandler(env=env).install(
        packages=Packages.from_specs("pyspark"), strict_channel_priority=False
    )

    history = env_io.get_history()

    expected_logs = expected["logs"].copy()
    expected_packages = copy.deepcopy(expected["packages"])

    expected_packages["conda"]["pyspark"] = Package.from_spec("pyspark")
    expected_logs.append(f"conda install --name {env.name} pyspark")

    install_channel_string = "--override-channels " + " ".join(
        f"--channel {channel}" for channel in expected["channels"]
    )

    action = (
        f"conda install --name {env.name} pyspark=0.21=py_36 {install_channel_string}"
    )

    expected_actions = expected["actions"].copy()
    expected_actions.append(action)

    assert history.packages == expected_packages
    assert history.actions == expected_actions
    assert history.logs == expected_logs


@pytest.mark.parametrize("use_package", (True, False))
def test_strict_channel_priority_update_all(setup_env, use_package, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    get_package_mock = setup_env["get_package_mock"]
    get_package_mock.configure_mock(
        return_value={
            "conda": {
                "pyspark": Package("pyspark", "pyspark", "2.3.2", "py_36"),
                "pandas": Package("pandas", "pandas", "0.23", "py_36"),
            }
        }
    )

    mocker.patch("conda_env_tracker.conda.conda_update_all")

    expected_packages = copy.deepcopy(expected["packages"])

    expected_packages["conda"]["pandas"] = Package.from_spec("pandas")

    update_all_channel_string = "--override-channels " + " ".join(
        f"--channel {channel}" for channel in expected["channels"]
    )

    if use_package:
        CondaHandler(env=env).update_all(
            packages=Packages.from_specs("pyspark"), strict_channel_priority=False
        )
        expected_packages["conda"]["pyspark"] = Package.from_spec("pyspark")
        log = f"conda update --all --name {env.name} pyspark"
        action = f"conda update --all --name {env.name} pyspark=2.3.2=py_36 {update_all_channel_string}"
    else:
        CondaHandler(env=env).update_all(strict_channel_priority=False)
        log = f"conda update --all --name {env.name}"
        action = f"conda update --all --name {env.name} {update_all_channel_string}"

    history = env_io.get_history()

    expected_logs = expected["logs"].copy()
    expected_logs.append(log)

    expected_actions = expected["actions"].copy()
    expected_actions.append(action)

    assert history.packages == expected_packages
    assert history.actions == expected_actions
    assert history.logs == expected_logs
