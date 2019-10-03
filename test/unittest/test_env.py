"""Test conda-env-tracker environment functions."""
# pylint: disable=redefined-outer-name, bad-continuation
from pathlib import Path
import shutil

import pytest

from conda_env_tracker.env import Environment
from conda_env_tracker.gateways.io import EnvIO, USER_ENVS_DIR
from conda_env_tracker.history import History
from conda_env_tracker.packages import Package, Packages


def test_create_success(setup_env):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = setup_env["expected"]

    assert env.name == env.name

    history = env_io.get_history()
    assert history.channels == expected["channels"]
    assert history.packages == expected["packages"]
    assert history.logs == expected["logs"]
    assert history.actions == expected["actions"]


def test_create_fail_existing_env(mocker):
    get_env_mock = mocker.patch("conda_env_tracker.env.get_all_existing_environment")
    env_name = "test-name"
    get_env_mock.configure_mock(return_value=env_name)
    mocker.patch("conda_env_tracker.env.prompt_yes_no").return_value = False
    with pytest.raises(Exception) as err:
        Environment.create(name=env_name, packages=["pandas"])
    assert str(err.value) == f"Environment {env_name} already exists"


def test_create_fail_base_env():
    with pytest.raises(Exception) as err:
        Environment.create(name="base", packages=["pandas"])
    assert str(err.value) == "Environment can not be created using default name base"


def test_replace_existing_env_success(mocker):
    mocker.patch("conda_env_tracker.env.delete_conda_environment")
    mocker.patch("conda_env_tracker.env.prompt_yes_no").return_value = True
    env_name = "conda_env_tracker-test-create-history"
    create_cmd = f"conda create --name {env_name} pandas"
    channels = ["conda-forge", "main"]
    packages = Packages.from_specs("pandas")
    action = "pandas=0.23=py_36"

    mocker.patch("conda_env_tracker.env.get_all_existing_environment").return_value = [
        env_name
    ]
    mocker.patch(
        "conda_env_tracker.env.conda_create", mocker.Mock(return_value=create_cmd)
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(
            return_value={
                "conda": {"pandas": Package("pandas", "*", "0.23=py_36")},
                "pip": {},
            }
        ),
    )
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_conda_channels", mocker.Mock(return_value=channels)
    )
    Environment.create(name=env_name, packages=packages)

    writer = EnvIO(env_directory=USER_ENVS_DIR / env_name)
    history = writer.get_history()
    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        "--channel " + channel for channel in channels
    )
    assert history.actions == [
        f"conda create --name {env_name} {action} {channel_string}"
    ]
    assert history.packages == {"conda": {"pandas": Package.from_spec("pandas")}}
    assert history.channels == channels
    assert history.logs == [create_cmd]

    env_dir = Path(USER_ENVS_DIR) / env_name
    shutil.rmtree(env_dir)


def test_create_history_success(mocker):
    env_name = "conda_env_tracker-test-create-history"
    create_cmd = f"conda create --name {env_name} pandas"
    channels = ["conda-forge", "main"]
    packages = Packages.from_specs("pandas")
    action = "pandas=0.23=py_36"

    mocker.patch("conda_env_tracker.env.get_all_existing_environment")
    mocker.patch(
        "conda_env_tracker.env.conda_create", mocker.Mock(return_value=create_cmd)
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(
            return_value={
                "conda": {"pandas": Package("pandas", "*", "0.23=py_36")},
                "pip": {},
            }
        ),
    )
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_conda_channels", mocker.Mock(return_value=channels)
    )
    Environment.create(name=env_name, packages=packages)

    writer = EnvIO(env_directory=USER_ENVS_DIR / env_name)
    history = writer.get_history()
    channel_string = "--override-channels --strict-channel-priority " + " ".join(
        "--channel " + channel for channel in channels
    )
    assert history.actions == [
        f"conda create --name {env_name} {action} {channel_string}"
    ]
    assert history.packages == {"conda": {"pandas": Package.from_spec("pandas")}}
    assert history.channels == channels
    assert history.logs == [create_cmd]

    env_dir = Path(USER_ENVS_DIR) / env_name
    shutil.rmtree(env_dir)


@pytest.mark.parametrize(
    "channels, effective_added_channels",
    [
        (["pro"], ["pro"]),
        (["pro", "r"], ["pro", "r"]),
        (["main"], []),
        (["main", "pro"], ["pro"]),
    ],
)
def test_update_channel(setup_env, channels, effective_added_channels):
    """We do never add main to the list of channels because
    the original list of channels already contains main
    """
    channels_at_start = setup_env["channels"]
    env = setup_env["env"]
    env_io = setup_env["env_io"]

    env.append_channels(channels=channels)

    expected = channels_at_start + effective_added_channels
    assert env_io.get_history().channels == expected


def test_export(mocker):
    name = "test-export"

    io_mock = mocker.patch("conda_env_tracker.env.EnvIO")
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(
            return_value={
                "conda": {"python": Package("python", "python", "3.7.2", "buildstr")},
                "pip": {},
            }
        ),
    )
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )

    history = History.parse(
        {
            "name": name,
            "channels": ["conda-forge", "main"],
            "packages": {"conda": {"python": "python=3.7"}},
            "revisions": [
                {
                    "log": "conda create --name test python=3.7",
                    "action": "conda create --name test python=3.7.2=buildstr",
                    "packages": {"conda": {"python": "python=3.7"}},
                    "diff": {"conda": {"upsert": ["python=3.7.2"]}},
                    "debug": {
                        "platform": "osx",
                        "conda_version": "4.6.1",
                        "pip_version": "18.1",
                    },
                }
            ],
        }
    )

    env = Environment(name=name, history=history)

    env.export()

    expected = """name: test-export
channels:
- conda-forge
- main
- nodefaults
dependencies:
- python=3.7.2
"""

    assert io_mock.mock_calls == [
        mocker.call(env_directory=Path(USER_ENVS_DIR / name)),
        mocker.call().write_history_file(history=history),
        mocker.call().export_packages(contents=expected),
        mocker.call().delete_install_r(),
    ]


def test_export_pip(mocker):
    name = "test-export"

    io_mock = mocker.patch("conda_env_tracker.env.EnvIO")
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(
            return_value={
                "conda": {"python": Package("python", "python", "3.7.2", "buildstr")},
                "pip": {"pytest": Package("pytest", "pytest", "4.0.0", None)},
            }
        ),
    )

    history = History.parse(
        {
            "name": name,
            "channels": ["conda-forge", "main"],
            "packages": {"conda": {"python": "3.7"}, "pip": {"pytest": "*"}},
            "revisions": [
                {
                    "log": "conda create --name test python=3.7",
                    "action": "conda create --name test python=3.7.2=buildstr",
                    "packages": {"conda": {"python": "3.7"}},
                    "diff": {"conda": {"upsert": ["python=3.7.2"]}},
                    "debug": {
                        "platform": "osx",
                        "conda_version": "4.6.1",
                        "pip_version": "18.1",
                    },
                },
                {
                    "log": "pip install pytest",
                    "action": "pip install pytest==4.0.0",
                    "packages": {"conda": {"python": "3.7"}, "pip": {"pytest": "*"}},
                    "diff": {"pip": {"upsert": ["pytest==4.0.0"]}},
                    "debug": {
                        "platform": "osx",
                        "conda_version": "4.6.1",
                        "pip_version": "18.1",
                    },
                },
            ],
        }
    )

    env = Environment(name=name, history=history)

    env.export()

    expected = """name: test-export
channels:
- conda-forge
- main
- nodefaults
dependencies:
- python=3.7.2
- pip:
  - pytest==4.0.0
"""

    assert io_mock.mock_calls == [
        mocker.call(env_directory=Path(USER_ENVS_DIR / name)),
        mocker.call().write_history_file(history=history),
        mocker.call().export_packages(contents=expected),
        mocker.call().delete_install_r(),
    ]


def test_infer_environment_success(mocker):
    env_name = "infer-test"
    dependencies = {"conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")}}
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_all_existing_environment", return_value=[env_name]
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies", mocker.Mock(return_value=dependencies)
    )
    mocker.patch("conda_env_tracker.env.get_r_dependencies")

    env = Environment.infer(
        name=env_name,
        packages=Packages.from_specs("pandas"),
        channels=["conda-forge", "main"],
    )
    assert env.history.packages == {
        "conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")}
    }
    assert env.history.channels == ["conda-forge", "main"]
    assert env.history.logs == [
        f"conda create --name {env_name} pandas --override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main"
    ]
    assert env.history.actions == [
        f"conda create --name {env_name} pandas=0.23=py_36 "
        "--override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main"
    ]


def test_infer_environment_with_spec_success(mocker):
    env_name = "infer-test"
    dependencies = {"conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")}}
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_all_existing_environment", return_value=[env_name]
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies", mocker.Mock(return_value=dependencies)
    )
    mocker.patch("conda_env_tracker.env.get_r_dependencies")

    env = Environment.infer(
        name=env_name,
        packages=Packages.from_specs("pandas=0.23"),
        channels=["conda-forge", "main"],
    )
    assert env.history.packages == {
        "conda": {"pandas": Package("pandas", "pandas=0.23", "0.23", "py_36")}
    }
    assert env.history.channels == ["conda-forge", "main"]
    assert env.history.logs == [
        f"conda create --name {env_name} pandas=0.23 --override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main"
    ]
    assert env.history.actions == [
        f"conda create --name {env_name} pandas=0.23=py_36 "
        "--override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main"
    ]


def test_infer_environment_does_not_exist(mocker):
    env_name = "infer-test"
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_all_existing_environment",
        return_value=["env-not-exist"],
    )
    with pytest.raises(Exception) as err:
        Environment.infer(
            name=env_name,
            packages=Packages.from_specs("pandas"),
            channels=["conda-forge", "main"],
        )
    assert (
        str(err.value) == f"Environment {env_name} can not be inferred, does not exist"
    )


def test_infer_environment_package_does_not_exist(mocker):
    env_name = "infer-test"
    dependencies = {"conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")}}
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_all_existing_environment", return_value=[env_name]
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies", mocker.Mock(return_value=dependencies)
    )
    mocker.patch("conda_env_tracker.env.get_r_dependencies")

    with pytest.raises(Exception) as err:
        Environment.infer(
            name=env_name,
            packages=Packages.from_specs("pytest"),
            channels=["conda-forge", "main"],
        )
    assert str(err.value) == "Environment infer-test does not have pytest installed"


def test_infer_environment_with_pip_package_success(mocker):
    env_name = "infer-test"
    dependencies = {
        "conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")},
        "pip": {"pytest": Package("pytest", "pytest", "0.11")},
    }
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch(
        "conda_env_tracker.env.get_all_existing_environment", return_value=[env_name]
    )
    mocker.patch(
        "conda_env_tracker.env.get_dependencies", mocker.Mock(return_value=dependencies)
    )
    mocker.patch("conda_env_tracker.env.get_r_dependencies")

    env = Environment.infer(
        name=env_name,
        packages=Packages.from_specs(["pandas", "pytest"]),
        channels=["conda-forge", "main"],
    )
    assert env.history.packages == {
        "conda": {"pandas": Package("pandas", "pandas", "0.23", "py_36")},
        "pip": {"pytest": Package("pytest", "pytest", "0.11")},
    }
    assert env.history.channels == ["conda-forge", "main"]
    assert env.history.logs == [
        f"conda create --name {env_name} pandas --override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main",
        "pip install pytest --index-url https://pypi.org/simple",
    ]
    assert env.history.actions == [
        f"conda create --name {env_name} pandas=0.23=py_36 "
        "--override-channels --strict-channel-priority "
        "--channel conda-forge "
        "--channel main",
        "pip install pytest==0.11 --index-url" " https://pypi.org/simple",
    ]
