"""Taken from pytest-ordering, https://github.com/ftobia/pytest-ordering/blob/develop/pytest_ordering/__init__.py"""
import shutil
from pathlib import Path

import pytest

from conda_env_tracker.errors import CondaEnvTrackerCondaError
from conda_env_tracker.gateways.conda import delete_conda_environment
from conda_env_tracker.gateways.io import USER_ENVS_DIR
from conda_env_tracker.main import create, setup_remote


@pytest.fixture(scope="module")
def end_to_end_setup(request):
    """Setup and teardown for tests."""
    name = "end_to_end_test"
    channels = ["defaults"]
    env_dir = USER_ENVS_DIR / name

    remote_path = Path(__file__).parent.absolute() / "remote_test_dir"
    if remote_path.exists():
        shutil.rmtree(remote_path)
    remote_path.mkdir()

    def teardown():
        delete_conda_environment(name=name)
        if env_dir.is_dir():
            shutil.rmtree(env_dir)
        if remote_path.is_dir():
            shutil.rmtree(remote_path)

    request.addfinalizer(teardown)

    try:
        env = create(
            name=name, specs=["python=3.6", "colorama"], channels=channels, yes=True
        )
        setup_remote(name=name, remote_dir=remote_path, yes=True)
    except CondaEnvTrackerCondaError as err:
        teardown()
        raise err

    channel_command = (
        "--override-channels --strict-channel-priority --channel "
        + " --channel ".join(channels)
    )

    return {
        "name": name,
        "env": env,
        "env_dir": env_dir,
        "channels": channels,
        "channel_command": channel_command,
        "remote_dir": remote_path,
    }


@pytest.fixture(scope="module")
def r_end_to_end_setup(request):
    """Setup and teardown for R end to end tests."""
    name = "r_end_to_end_test"
    channels = ["r", "defaults"]
    env_dir = USER_ENVS_DIR / name

    remote_path = Path(__file__).parent.absolute() / "remote_test_dir"
    if remote_path.exists():
        shutil.rmtree(remote_path)
    remote_path.mkdir()

    def teardown():
        delete_conda_environment(name=name)
        if env_dir.is_dir():
            shutil.rmtree(env_dir)
        if remote_path.is_dir():
            shutil.rmtree(remote_path)

    request.addfinalizer(teardown)

    try:
        env = create(
            name=name, specs=["r-base", "r-devtools"], channels=channels, yes=True
        )
        setup_remote(name=name, remote_dir=remote_path, yes=True)
    except CondaEnvTrackerCondaError as err:
        teardown()
        raise err

    return {
        "name": name,
        "env": env,
        "env_dir": env_dir,
        "channels": channels,
        "remote_dir": remote_path,
    }
