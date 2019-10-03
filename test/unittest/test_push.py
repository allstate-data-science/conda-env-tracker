"""Test cases for conda push to remote"""
# pylint: disable=redefined-outer-name
import shutil

import pytest

from conda_env_tracker.channels import Channels
from conda_env_tracker.gateways.io import USER_ENVS_DIR
from conda_env_tracker.history import Debug, Diff, History, Logs, PackageRevision
from conda_env_tracker.env import Environment
from conda_env_tracker.errors import CondaEnvTrackerPushError, PUSH_ERROR_STR
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.push import push


@pytest.fixture(
    params=[
        {
            "env_name": "test-push-success",
            "push_should_fail": False,
            "local_packages": Packages.from_specs(["pandas", "pytest"]),
            "local_logs": [
                "conda create --name test-push-success pandas",
                "conda install --name test-push-success pytest",
            ],
            "local_actions": [
                "conda create --name test-push-success pandas=0.23.0=py36",
                "conda install --name test-push-success pytest=4.0.0=py36",
            ],
            "remote_packages": Packages.from_specs(["pandas", "pylint"]),
            "remote_logs": ["conda create --name test-push-success pandas"],
            "remote_actions": [
                "conda create --name test-push-success pandas=0.23.0=py36"
            ],
        },
        {
            "env_name": "test-push-fail",
            "push_should_fail": True,
            "local_packages": Packages.from_specs(["pandas", "pytest"]),
            "local_logs": [
                "conda create --name test-push-fail pandas",
                "conda install --name test-push-fail pytest",
            ],
            "local_actions": [
                "conda create --name test-push-fail pandas=0.23.0=py36",
                "conda install --name test-push-fail pytest=4.0.0=py36",
            ],
            "remote_packages": Packages.from_specs(["pandas", "xgboost"]),
            "remote_logs": [
                "conda create --name test-push-fail pandas",
                "conda install --name test-push-fail xgboost",
            ],
            "remote_actions": [
                "conda create --name test-push-fail pandas=0.23.0=py36",
                "conda install --name test-push-fail xgboost=0.7=py36",
            ],
        },
        {
            "env_name": "test-push-fail",
            "push_should_fail": True,
            "local_packages": Packages.from_specs(["pandas", "numpy", "pytest"]),
            "local_logs": [
                "conda create --name test-push-fail pandas",
                "conda install --name test-push-fail numpy",
                "conda install --name test-push-fail pytest",
            ],
            "local_actions": [
                "conda create --name test-push-fail pandas=0.23.0=py36",
                "conda install --name test-push-fail numpy=1.1.15=py36",
                "conda install --name test-push-fail pytest=4.0.0=py36",
            ],
            "remote_packages": Packages.from_specs(["pandas", "numpy", "pytest"]),
            "remote_logs": [
                "conda create --name test-push-fail pandas",
                "conda install --name test-push-fail pytest",
                "conda install --name test-push-fail numpy",
            ],
            "remote_actions": [
                "conda create --name test-push-fail pandas=0.23.0=py36",
                "conda install --name test-push-fail pytest=4.0.0=py36",
                "conda install --name test-push-fail numpy=1.1.15=py36",
            ],
        },
    ]
)
def setup(mocker, request):
    """Set up for diff function"""
    local_packages = request.param["local_packages"]
    local_logs = request.param["local_logs"]
    local_actions = request.param["local_actions"]
    env_name = request.param["env_name"]

    remote_packages = request.param["remote_packages"]
    remote_logs = request.param["remote_logs"]
    remote_actions = request.param["remote_actions"]

    dependencies = {
        "conda": {
            "pandas": Package("pandas", "pandas", version="0.23.0"),
            "pytest": Package("pytest", "pytest", version="4.0.0"),
        }
    }
    mocker.patch(
        "conda_env_tracker.env.get_dependencies", mocker.Mock(return_value=dependencies)
    )
    history = History.create(
        name=env_name,
        packages=PackageRevision.create(local_packages, dependencies=dependencies),
        channels=Channels(["conda-forge"]),
        logs=Logs([log for log in local_logs]),
        actions=local_actions,
        diff=Diff(),
        debug=Debug(),
    )
    env = Environment(name=env_name, history=history)
    mocker.patch("conda_env_tracker.main.Environment.read", return_value=env)

    mocker.patch(
        "conda_env_tracker.gateways.io.EnvIO.get_remote_dir",
        return_value="~/path/to/remote",
    )
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    history = History.create(
        name=env_name,
        channels=Channels(["conda-forge"]),
        packages=PackageRevision.create(remote_packages, dependencies=dependencies),
        logs=Logs([log for log in remote_logs]),
        actions=remote_actions,
        diff=Diff(),
        debug=Debug(),
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.EnvIO.get_history", return_value=history
    )
    mocker.patch("pathlib.Path.write_text")

    yield env, request.param["push_should_fail"]

    if (USER_ENVS_DIR / env_name).exists():
        shutil.rmtree(USER_ENVS_DIR / env_name)


def test_push(setup):
    env, push_should_fail = setup
    if push_should_fail:
        with pytest.raises(CondaEnvTrackerPushError) as err:
            push(env=env)
            assert str(err.value) == PUSH_ERROR_STR.format(
                remote_dir="~/path/to/remote", local_dir=env.user_envs_dir / "test-push"
            )
    else:
        push(env=env)
        assert env.history.packages == {
            "conda": {
                "pandas": Package("pandas", "pandas", "0.23.0"),
                "pytest": Package("pytest", "pytest", "4.0.0"),
            }
        }
        assert env.history.logs == [
            f"conda create --name {env.name} pandas",
            f"conda install --name {env.name} pytest",
        ]
        assert env.history.actions == [
            f"conda create --name {env.name} pandas=0.23.0=py36",
            f"conda install --name {env.name} pytest=4.0.0=py36",
        ]
