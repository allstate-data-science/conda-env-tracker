"""Test pip functionality."""
# pylint: disable=redefined-outer-name
import os
import re
from datetime import date

import oyaml as yaml
import pytest


from conda_env_tracker.errors import PipInstallError
from conda_env_tracker.gateways import pip
from conda_env_tracker.gateways.conda import CONDA_VERSION, get_dependencies
from conda_env_tracker.gateways.utils import get_platform_name
from conda_env_tracker.main import pip_install, pip_remove
from conda_env_tracker.packages import Packages


@pytest.fixture(scope="module")
def pip_setup(end_to_end_setup):
    """Doing pip install to setup for testing history and conda env yaml files."""
    pip_install(
        name=end_to_end_setup["name"], specs=["pytest==4.0.0", "pytest-cov"], yes=True
    )
    return end_to_end_setup


@pytest.mark.run(order=-11)
def test_history_pip_install(pip_setup):
    """Test the history.yaml in detail."""
    name = pip_setup["name"]
    env_dir = pip_setup["env_dir"]
    channels = pip_setup["channels"]

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    pip_action_exp = rf"(pip install pytest==4.0.0)(\s)(pytest-cov==)(.*)(--index-url {pip.PIP_DEFAULT_INDEX_URL})"

    expected_packages = {
        "conda": {"colorama": "*", "python": "3.6"},
        "pip": {"pytest": "4.0.0", "pytest-cov": "*"},
    }
    expected_log = (
        f"pip install pytest==4.0.0 pytest-cov --index-url {pip.PIP_DEFAULT_INDEX_URL}"
    )
    expected_debug = 2 * [
        {
            "platform": get_platform_name(),
            "conda_version": CONDA_VERSION,
            "pip_version": pip.get_pip_version(name=name),
            "timestamp": str(date.today()),
        }
    ]
    assert actual["name"] == name
    assert actual["channels"] == channels
    assert actual["packages"] == expected_packages
    assert actual["logs"][-1] == expected_log
    assert len(actual["logs"]) == 2
    assert re.match(pip_action_exp, actual["actions"][-1])
    assert len(actual["actions"]) == 2
    for i in range(len(actual["debug"])):
        for key, val in expected_debug[i].items():
            if key == "timestamp":
                assert actual["debug"][i][key].startswith(val)
            else:
                assert actual["debug"][i][key] == val

    expected_history = [f"name: {name}", "channels:"]
    for channel in channels:
        expected_history.append(f"  - {channel}")
    expected_history_start = "\n".join(
        expected_history
        + [
            "packages:",
            "  conda:",
            "    python: '3.6'",
            "    colorama: '*'",
            "  pip:",
            "    pytest: 4.0.0",
            "    pytest-cov: '*'",
            "logs:",
            "  - conda create --name end_to_end_test python=3.6 colorama --override-channels --strict-channel-priority",
            "    --channel main",
            f"  - {expected_log}",
            "actions:",
            f"  - conda create --name {name} python=3.6",
        ]
    )
    end = actual_history_content.rfind("python=3.6") + len("python=3.6")
    actual_history_start = actual_history_content[:end]
    assert actual_history_start == expected_history_start


@pytest.mark.run(order=-10)
def test_conda_env_yaml_pip_install(pip_setup):
    """Test the conda-env.yaml file in detail."""
    name = pip_setup["name"]
    env_dir = pip_setup["env_dir"]
    channels = pip_setup["channels"]

    packages = get_dependencies(name=name)
    conda_packages = packages["conda"]
    pip_packages = packages["pip"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_conda_packages = [
        "  - python=" + conda_packages["python"].version,
        "  - colorama=" + conda_packages["colorama"].version,
    ]

    expected_pip_packages = [
        "    - pytest==" + pip_packages["pytest"].version,
        "    - pytest-cov==" + pip_packages["pytest-cov"].version,
    ]

    expected = (
        "\n".join(
            expected_start
            + expected_conda_packages
            + ["  - pip:"]
            + expected_pip_packages
        )
        + "\n"
    )

    actual = (env_dir / "conda-env.yaml").read_text()
    print(actual)
    assert actual == expected


@pytest.mark.run(order=-9)
def test_pip_remove(pip_setup):
    name = pip_setup["name"]
    env_dir = pip_setup["env_dir"]
    channels = pip_setup["channels"]

    history_file = env_dir / "history.yaml"
    pip_remove(name=name, specs=["pytest-cov"], yes=True)
    actual_history_content = history_file.read_text()
    print(actual_history_content)
    expected_packages = {
        "conda": {"colorama": "*", "python": "3.6"},
        "pip": {"pytest": "4.0.0"},
    }
    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    expected_log = "pip uninstall pytest-cov"
    assert actual["packages"] == expected_packages
    assert actual["logs"][-1] == expected_log
    assert actual["actions"][-1] == expected_log

    packages = get_dependencies(name=name)
    conda_packages = packages["conda"]
    pip_packages = packages["pip"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_conda_packages = [
        "  - python=" + conda_packages["python"].version,
        "  - colorama=" + conda_packages["colorama"].version,
    ]

    expected_pip_packages = ["    - pytest==" + pip_packages["pytest"].version]

    expected = (
        "\n".join(
            expected_start
            + expected_conda_packages
            + ["  - pip:"]
            + expected_pip_packages
        )
        + "\n"
    )

    actual = (env_dir / "conda-env.yaml").read_text()
    print(actual)
    assert actual == expected


def test_env_name_error():
    with pytest.raises(PipInstallError) as err:
        pip.pip_install(name="thisistotallynotthenameofanenvironment", packages=[])
    assert str(err.value) == (
        "Pip install [] failed with message: Could not find conda environment: thisistotallynotthenameofanenvironment\n"
        "You can list all discoverable environments with `conda info --envs`.\n\n"
    )


def test_package_name_error():
    name = os.environ.get("CONDA_DEFAULT_ENV")
    with pytest.raises(PipInstallError):
        pip.pip_install(
            name=name,
            packages=Packages.from_specs(
                ["thereisnowaysomeonewouldnameapackagethisway"]
            ),
        )


def test_pip_version():
    name = os.environ.get("CONDA_DEFAULT_ENV")
    if name:
        version = pip.get_pip_version(name=name)
        assert isinstance(version, str)
        assert version >= "18.1"
