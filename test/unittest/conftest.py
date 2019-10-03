"""Setting up an instance of the Environment class to use in several tests."""

import shutil

import pytest

from conda_env_tracker import main
from conda_env_tracker.gateways.io import EnvIO, USER_ENVS_DIR
from conda_env_tracker.packages import Package

ENV_NAME = "conda_env_tracker-test-create"


@pytest.fixture(
    scope="function",
    params=[
        {
            "input": {"specs": ["pandas"], "yes": True},
            "expected": {
                "logs": [f"conda create --name {ENV_NAME} pandas"],
                "actions": [
                    f"conda create --name {ENV_NAME} pandas=0.23=py_36 --override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ],
                "packages": {"conda": {"pandas": Package.from_spec("pandas")}},
                "channels": ["conda-forge", "main"],
            },
        },
        {
            "input": {"specs": ["pandas=0.23=py_36"]},
            "expected": {
                "logs": [f"conda create --name {ENV_NAME} pandas=0.23=py_36"],
                "actions": [
                    f"conda create --name {ENV_NAME} pandas=0.23=py_36 --override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ],
                "packages": {
                    "conda": {"pandas": Package.from_spec("pandas=0.23=py_36")}
                },
                "channels": ["conda-forge", "main"],
            },
        },
        {
            "input": {"specs": ["pandas=0.23"]},
            "expected": {
                "logs": [f"conda create --name {ENV_NAME} pandas=0.23"],
                "actions": [
                    f"conda create --name {ENV_NAME} pandas=0.23=py_36 --override-channels --strict-channel-priority "
                    "--channel conda-forge "
                    "--channel main"
                ],
                "packages": {"conda": {"pandas": Package.from_spec("pandas=0.23")}},
                "channels": ["conda-forge", "main"],
            },
        },
        {
            "input": {"specs": ["pandas=0.23"], "channels": ["main"]},
            "expected": {
                "logs": [
                    f"conda create --name {ENV_NAME} pandas=0.23 --override-channels --strict-channel-priority "
                    "--channel main"
                ],
                "actions": [
                    f"conda create --name {ENV_NAME} pandas=0.23=py_36 --override-channels --strict-channel-priority "
                    "--channel main"
                ],
                "packages": {"conda": {"pandas": Package.from_spec("pandas=0.23")}},
                "channels": ["main"],
            },
        },
        {
            "input": {
                "specs": ["pandas=0.23"],
                "channels": ["main"],
                "strict_channel_priority": False,
            },
            "expected": {
                "logs": [
                    f"conda create --name {ENV_NAME} pandas=0.23 --override-channels "
                    "--channel main"
                ],
                "actions": [
                    f"conda create --name {ENV_NAME} pandas=0.23=py_36 --override-channels "
                    "--channel main"
                ],
                "packages": {"conda": {"pandas": Package.from_spec("pandas=0.23")}},
                "channels": ["main"],
            },
        },
    ],
)
def setup_env(mocker, request):
    """Setup and teardown for tests with parameterized inputs. Even yes is passed in commands like create and install,
    the option itself don't show up in actions and logs as it provide no additional value for reproducibility."""
    env_dir = USER_ENVS_DIR / ENV_NAME
    mocker.patch(
        "conda_env_tracker.history.debug.get_pip_version",
        mocker.Mock(return_value="18.1"),
    )
    mocker.patch("conda_env_tracker.env.get_all_existing_environment")
    mocker.patch("conda_env_tracker.main._ask_user_to_sync")
    mocker.patch("conda_env_tracker.gateways.conda.run_command")
    initial_conda_packages = {"pandas": Package("pandas", "pandas", "0.23", "py_36")}
    get_package_mock = mocker.patch(
        "conda_env_tracker.env.get_dependencies",
        mocker.Mock(return_value={"conda": initial_conda_packages, "pip": {}}),
    )
    condarc_channels = ["conda-forge", "main"]
    mocker.patch(
        "conda_env_tracker.env.get_conda_channels",
        mocker.Mock(return_value=condarc_channels),
    )
    if "channels" in request.param["input"]:
        channels = request.param["input"]["channels"]
    else:
        channels = condarc_channels
    id_mock = mocker.patch("conda_env_tracker.history.history.uuid4")
    id_mock.return_value = "my_unique_id"
    env = main.create(name=ENV_NAME, **request.param["input"])
    env_io = EnvIO(env_directory=env_dir)
    yield {
        "channels": channels,
        "env": env,
        "env_io": env_io,
        "expected": request.param["expected"],
        "get_package_mock": get_package_mock,
        "initial_conda_packages": initial_conda_packages,
        "id": id_mock,
    }
    if env_dir.exists():
        shutil.rmtree(env_dir)
