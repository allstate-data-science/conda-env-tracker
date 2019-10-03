"""Test the history and environment.yml file after create and install."""
import re
import subprocess
from datetime import date

import pytest
import oyaml as yaml

from conda_env_tracker.main import conda_install, conda_remove
from conda_env_tracker.gateways.conda import (
    CONDA_VERSION,
    get_dependencies,
    get_all_existing_environment,
)
from conda_env_tracker.gateways.pip import get_pip_version
from conda_env_tracker.gateways.utils import get_platform_name


@pytest.mark.run(order=-7)
def test_history_after_create(end_to_end_setup):
    """Test the history.yaml in detail."""
    name = end_to_end_setup["name"]
    env = end_to_end_setup["env"]
    env_dir = end_to_end_setup["env_dir"]
    channels = end_to_end_setup["channels"]
    channel_command = end_to_end_setup["channel_command"]

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    action_expected_pattern = rf"(conda create --name {name})(\s)(python=3.6)(.*)(\s)(colorama=)(.*)({channel_command})"

    expected_packages = {"conda": {"colorama": "*", "python": "python=3.6"}}
    expected_log = f"conda create --name {name} python=3.6 colorama {channel_command}"

    expected_debug = [
        {
            "platform": get_platform_name(),
            "conda_version": CONDA_VERSION,
            "pip_version": get_pip_version(name=name),
            "timestamp": str(date.today()),
        }
    ]

    assert actual["packages"] == expected_packages
    assert actual["revisions"][-1]["log"] == expected_log
    assert actual["channels"] == channels
    assert re.match(action_expected_pattern, actual["revisions"][0]["action"])
    for key, val in expected_debug[0].items():
        if key == "timestamp":
            assert actual["revisions"][0]["debug"][key].startswith(val)
        else:
            assert actual["revisions"][0]["debug"][key] == val

    conda_dependencies = env.dependencies["conda"]

    expected_start = [
        f"name: {name}",
        f"id: {env.history.id}",
        "history-file-version: '1.0'",
        "channels:",
    ]
    for channel in channels:
        expected_start.append(f"  - {channel}")
    expected_history_start = "\n".join(
        expected_start
        + [
            "packages:",
            "  conda:",
            "    python: python=3.6",
            "    colorama: '*'",
            "revisions:",
            "  - packages:",
            "      conda:",
            "        python: python=3.6",
            "        colorama: '*'",
            "    diff:",
            "      conda:",
            "        upsert:",
            f"        - python={conda_dependencies['python'].version}",
            f"        - colorama={conda_dependencies['colorama'].version}",
            f"    log: conda create --name {name} python=3.6 colorama --override-channels",
            "      --strict-channel-priority --channel main",
            f"    action: conda create --name {name} python=3.6",
        ]
    )
    first_action_start = f"action: conda create --name {name} python=3.6"
    index_first_action = actual_history_content.find(first_action_start) + len(
        first_action_start
    )
    actual_history_start = actual_history_content[:index_first_action]
    assert actual_history_start == expected_history_start


@pytest.mark.run(order=-6)
def test_conda_env_yaml_after_create(end_to_end_setup):
    """Test the environment.yml file in detail."""
    name = end_to_end_setup["name"]
    env_dir = end_to_end_setup["env_dir"]
    channels = end_to_end_setup["channels"]

    conda_packages = get_dependencies(name=name)["conda"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_packages = [
        "  - python=" + conda_packages["python"].version,
        "  - colorama=" + conda_packages["colorama"].version,
    ]

    expected = "\n".join(expected_start + expected_packages) + "\n"

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected


@pytest.mark.run(order=-5)
def test_history_after_install(end_to_end_setup):
    """Test the history.yaml file in detail after pytest has been installed."""
    name = end_to_end_setup["name"]

    env = conda_install(name=name, specs=["pytest>4.0,<6.0"], yes=True)

    env_dir = end_to_end_setup["env_dir"]
    channels = end_to_end_setup["channels"]
    channel_command = end_to_end_setup["channel_command"]

    log_file = env_dir / "history.yaml"
    actual_history_content = log_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    action_install_expected_pattern = (
        rf"(conda install --name {name})(\s)(pytest=)(.*)({channel_command})"
    )

    expected_packages = {
        "conda": {"colorama": "*", "python": "python=3.6", "pytest": "pytest>4.0,<6.0"}
    }
    expected_log = f'conda install --name {name} "pytest>4.0,<6.0"'
    expected_debug = 2 * [
        {
            "platform": get_platform_name(),
            "conda_version": CONDA_VERSION,
            "pip_version": get_pip_version(name=name),
            "timestamp": str(date.today()),
        }
    ]

    assert actual["packages"] == expected_packages
    assert len(actual["revisions"]) == 2
    assert actual["revisions"][-1]["log"] == expected_log
    assert actual["channels"] == channels
    assert re.match(action_install_expected_pattern, actual["revisions"][-1]["action"])
    for key, val in expected_debug[1].items():
        if key == "timestamp":
            assert actual["revisions"][1]["debug"][key].startswith(val)
        else:
            assert actual["revisions"][1]["debug"][key] == val

    # The packages section at the top of the file is current
    expected_packages_section = "\n".join(
        [
            "packages:",
            "  conda:",
            "    python: python=3.6",
            "    colorama: '*'",
            "    pytest: pytest>4.0,<6.0",
            "revisions:",
        ]
    )
    assert expected_packages_section in actual_history_content

    conda_dependencies = env.dependencies["conda"]

    expected_second_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        python: python=3.6",
            "        colorama: '*'",
            "        pytest: pytest>4.0,<6.0",
            "    diff:",
            "      conda:",
            "        upsert:",
            f"        - pytest={conda_dependencies['pytest'].version}",
            f'    log: conda install --name {name} "pytest>4.0,<6.0"',
            f"    action: conda install --name {name} pytest",
        ]
    )

    index_first_revision = actual_history_content.find("  - packages:")
    index_second_revision_start = actual_history_content.find(
        "  - packages:", index_first_revision + 1
    )
    second_action = f"action: conda install --name {name} pytest"
    index_second_action = actual_history_content.find(
        second_action, index_second_revision_start
    ) + len(second_action)
    actual_second_revision = actual_history_content[
        index_second_revision_start:index_second_action
    ]
    assert actual_second_revision == expected_second_revision


@pytest.mark.run(order=-4)
def test_conda_env_yaml_after_install(end_to_end_setup):
    """Test the environment.yml file in detail after pytest has been installed."""
    name = end_to_end_setup["name"]
    env_dir = end_to_end_setup["env_dir"]
    channels = end_to_end_setup["channels"]

    conda_packages = get_dependencies(name=name)["conda"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_packages = [
        "  - python=" + conda_packages["python"].version,
        "  - colorama=" + conda_packages["colorama"].version,
        "  - pytest=" + conda_packages["pytest"].version,
    ]

    expected = "\n".join(expected_start + expected_packages) + "\n"

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected


@pytest.mark.run(order=-3)
def test_rebuild(end_to_end_setup):
    """Test the rebuild of a conda_env_tracker folder and conda environment."""
    name = end_to_end_setup["name"]
    env = end_to_end_setup["env"]

    env_dir = end_to_end_setup["env_dir"]
    initial_history_content = (env_dir / "history.yaml").read_text()
    initial_env_file = (env_dir / "environment.yml").read_text()
    initial_process = subprocess.run(
        f"conda list --name {name} --revisions",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )
    initial_revisions = initial_process.stdout.split("\n")
    initial_revision_dates = [
        line for line in initial_revisions if line.startswith("2")
    ]

    env.rebuild()

    environments = get_all_existing_environment()
    assert name in environments

    final_history_content = (env_dir / "history.yaml").read_text()
    final_env_file = (env_dir / "environment.yml").read_text()
    assert final_env_file == initial_env_file
    assert final_history_content == initial_history_content

    final_process = subprocess.run(
        f"conda list --name {name} --revisions",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )
    final_revisions = final_process.stdout.split("\n")
    final_revision_dates = [line for line in final_revisions if line.startswith("2")]
    assert len(final_revision_dates) == 1
    assert "(rev 0)" in final_revision_dates[0]
    final_year_month_day, final_hour_minute_second = final_revision_dates[0].split()[
        0:2
    ]
    for time in initial_revision_dates:
        initial_year_month_day, initial_hour_minute_second = time.split()[0:2]
        assert final_year_month_day >= initial_year_month_day
        assert final_hour_minute_second >= initial_hour_minute_second


@pytest.mark.run(order=-2)
def test_remove_package(end_to_end_setup):
    """Test the removal of a package."""
    name = end_to_end_setup["name"]
    env_dir = end_to_end_setup["env_dir"]
    channels = end_to_end_setup["channels"]
    channel_command = end_to_end_setup["channel_command"].replace(
        "--strict-channel-priority ", ""
    )

    conda_remove(name=name, specs=["colorama"], yes=True)

    actual_env_content = (env_dir / "environment.yml").read_text()
    assert "colorama" not in actual_env_content

    log_file = env_dir / "history.yaml"
    actual_history_content = log_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    expected_packages = {"conda": {"python": "python=3.6", "pytest": "pytest>4.0,<6.0"}}
    expected_log = f"conda remove --name {name} colorama"
    expected_debug = {
        "platform": get_platform_name(),
        "conda_version": CONDA_VERSION,
        "pip_version": get_pip_version(name=name),
        "timestamp": str(date.today()),
    }

    assert actual["packages"] == expected_packages
    assert len(actual["revisions"]) == 3
    assert actual["revisions"][-1]["log"] == expected_log
    assert actual["channels"] == channels
    assert (
        actual["revisions"][-1]["action"]
        == f"conda remove --name {name} colorama {channel_command}"
    )
    for key, val in expected_debug.items():
        if key == "timestamp":
            assert actual["revisions"][2]["debug"][key].startswith(val)
        else:
            assert actual["revisions"][2]["debug"][key] == val

    # The packages section at the top of the file is current
    expected_packages_section = "\n".join(
        [
            "packages:",
            "  conda:",
            "    python: python=3.6",
            "    pytest: pytest>4.0,<6.0",
            "revisions:",
        ]
    )
    assert expected_packages_section in actual_history_content

    expected_third_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        python: python=3.6",
            "        pytest: pytest>4.0,<6.0",
            "    diff:",
            "      conda:",
            "        remove:",
            "        - colorama",
            f"    log: conda remove --name {name} colorama",
            f"    action: conda remove --name {name} colorama",
        ]
    )
    index_first_revision = actual_history_content.find("  - packages:")
    index_second_revision = actual_history_content.find(
        "  - packages:", index_first_revision + 1
    )
    index_third_revision = actual_history_content.find(
        "  - packages:", index_second_revision + 1
    )
    third_action = f"    action: {expected_log}"
    index_third_action = actual_history_content.find(
        third_action, index_third_revision
    ) + len(third_action)
    actual_third_revision = actual_history_content[
        index_third_revision:index_third_action
    ]
    assert actual_third_revision == expected_third_revision


@pytest.mark.run(order=-1)
def test_remove_environment(end_to_end_setup):
    """Test the removal of a conda_env_tracker folder and conda environment."""
    name = end_to_end_setup["name"]
    env = end_to_end_setup["env"]
    env_dir = end_to_end_setup["env_dir"]
    remote_dir = end_to_end_setup["remote_dir"]

    assert env_dir.exists()
    assert remote_dir.exists()

    env.remove(yes=True)

    environments = get_all_existing_environment()

    assert not remote_dir.exists()
    assert not env_dir.exists()
    assert name not in environments
