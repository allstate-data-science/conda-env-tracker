"""Test all conda_env_tracker remote push/pull features"""
# pylint: disable=redefined-outer-name, unused-argument
from datetime import date

import pytest

from conda_env_tracker.gateways.conda import get_dependencies, CONDA_VERSION
from conda_env_tracker.gateways.pip import get_pip_version
from conda_env_tracker.gateways.io import EnvIO, USER_ENVS_DIR
from conda_env_tracker.gateways.utils import get_platform_name
from conda_env_tracker.main import setup_remote, push, conda_install, pull
from conda_env_tracker.packages import Package


@pytest.mark.run(order=-8)  # Not required, just put slowest test at the end
def test_remote_end_to_end(end_to_end_setup, mocker):
    """Test setup, create, install, pull and push feature of conda_env_tracker"""
    env = end_to_end_setup["env"]
    remote_dir = end_to_end_setup["remote_dir"]
    channels = end_to_end_setup["channels"]
    channel_command = end_to_end_setup["channel_command"]

    setup_remote(name=env.name, remote_dir=remote_dir)

    local_io = EnvIO(env_directory=USER_ENVS_DIR / env.name)
    assert str(local_io.get_remote_dir()) == str(remote_dir)
    assert not list(remote_dir.glob("*"))

    push(name=env.name)
    remote_io = EnvIO(env_directory=remote_dir)
    assert remote_io.get_history() == local_io.get_history()
    assert remote_io.get_environment() == local_io.get_environment()

    env = conda_install(name=env.name, specs=["pytest"], yes=True)
    assert env.local_io.get_history() != remote_io.get_history()
    env = push(name=env.name)
    assert env.local_io.get_history() == remote_io.get_history()

    log_mock = mocker.patch("conda_env_tracker.pull.logging.Logger.info")
    env = pull(name=env.name)
    log_mock.assert_called_once_with("Nothing to pull.")

    remove_package_from_history(env, "pytest")

    conda_dependencies = env.dependencies["conda"]
    assert env.local_io.get_history() != remote_io.get_history()
    assert env.history.packages == {
        "conda": {
            "python": Package(
                "python",
                "python=3.6",
                version=conda_dependencies["python"].version,
                build=conda_dependencies["python"].build,
            ),
            "colorama": Package(
                "colorama",
                "colorama",
                version=conda_dependencies["colorama"].version,
                build=conda_dependencies["colorama"].build,
            ),
        }
    }

    env = pull(name=env.name)

    assert env.local_io.get_history() == remote_io.get_history()
    assert remote_io.get_environment() == local_io.get_environment()

    remove_package_from_history(env, "pytest")
    assert env.local_io.get_history() != remote_io.get_history()

    env = conda_install(
        name=env.name, specs=["pytest-cov"], channels=("main",), yes=True
    )
    env = pull(name=env.name, yes=True)

    conda_dependencies = env.dependencies["conda"]
    assert env.history.packages == {
        "conda": {
            "python": Package(
                "python",
                "python=3.6",
                version=conda_dependencies["python"].version,
                build=conda_dependencies["python"].build,
            ),
            "colorama": Package(
                "colorama",
                "colorama",
                version=conda_dependencies["colorama"].version,
                build=conda_dependencies["colorama"].build,
            ),
            "pytest": Package(
                "pytest",
                "pytest",
                version=conda_dependencies["pytest"].version,
                build=conda_dependencies["pytest"].build,
            ),
            "pytest-cov": Package(
                "pytest-cov",
                "pytest-cov",
                version=conda_dependencies["pytest-cov"].version,
                build=conda_dependencies["pytest-cov"].build,
            ),
        }
    }

    log_list = [
        f"conda create --name {env.name} python=3.6 colorama {channel_command}",
        f"conda install --name {env.name} pytest",
        f"conda install --name {env.name} pytest-cov --channel main",
    ]
    assert env.history.logs == log_list

    actual_env = (env.local_io.env_dir / "environment.yml").read_text()
    conda_dependencies = get_dependencies(name=env.name)["conda"]
    expected_env = [f"name: {env.name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_env.append(f"  - {channel}")
    expected_env = (
        "\n".join(
            expected_env
            + [
                "dependencies:",
                "  - python=" + conda_dependencies["python"].version,
                "  - colorama=" + conda_dependencies["colorama"].version,
                "  - pytest=" + conda_dependencies["pytest"].version,
                "  - pytest-cov=" + conda_dependencies["pytest-cov"].version,
            ]
        )
        + "\n"
    )
    assert actual_env == expected_env

    expected_debug = 3 * [
        {
            "platform": get_platform_name(),
            "conda_version": CONDA_VERSION,
            "pip_version": get_pip_version(name=env.name),
            "timestamp": str(date.today()),
        }
    ]
    for i in range(len(env.history.debug)):
        for key, val in expected_debug[i].items():
            if key == "timestamp":
                assert env.history.debug[i][key].startswith(val)
            else:
                assert env.history.debug[i][key] == val


def remove_package_from_history(env, package: str):
    """Remove package from environment history"""
    env.history.packages["conda"].pop(package)
    env.history.logs.pop(1)
    env.history.actions.pop(1)
    env.local_io.write_history_file(env.history)
