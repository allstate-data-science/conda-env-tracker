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
    env = pip_install(
        name=end_to_end_setup["name"], specs=["pytest==4.0.0", "pytest-cov"], yes=True
    )
    end_to_end_setup["env"] = env
    return end_to_end_setup


@pytest.mark.run(order=-11)
def test_history_pip_install(pip_setup):
    """Test the history.yaml in detail."""
    name = pip_setup["name"]
    env = pip_setup["env"]
    env_dir = pip_setup["env_dir"]
    channels = pip_setup["channels"]

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    pip_action_exp = rf"(pip install pytest==4.0.0)(\s)(pytest-cov==)(.*)(--index-url {pip.PIP_DEFAULT_INDEX_URL})"

    expected_packages = {
        "conda": {"colorama": "*", "python": "python=3.6"},
        "pip": {"pytest": "pytest==4.0.0", "pytest-cov": "*"},
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
    assert actual["revisions"][-1]["log"] == expected_log
    assert len(actual["revisions"]) == 2
    assert re.match(pip_action_exp, actual["revisions"][-1]["action"])
    for i in range(len(actual["revisions"])):
        for key, val in expected_debug[i].items():
            if key == "timestamp":
                assert actual["revisions"][i]["debug"][key].startswith(val)
            else:
                assert actual["revisions"][i]["debug"][key] == val

    # The packages section at the top of the file is current
    expected_packages_section = "\n".join(
        [
            "packages:",
            "  conda:",
            "    python: python=3.6",
            "    colorama: '*'",
            "  pip:",
            "    pytest: pytest==4.0.0",
            "    pytest-cov: '*'",
            "revisions:",
        ]
    )
    assert expected_packages_section in actual_history_content

    pip_dependencies = env.dependencies["pip"]

    expected_second_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        python: python=3.6",
            "        colorama: '*'",
            "      pip:",
            "        pytest: pytest==4.0.0",
            "        pytest-cov: '*'",
            "    diff:",
            "      pip:",
            "        upsert:",
            "        - pytest==4.0.0",
            f"        - pytest-cov=={pip_dependencies['pytest-cov'].version}",
            f"    log: pip install pytest==4.0.0 pytest-cov --index-url {pip.PIP_DEFAULT_INDEX_URL}",
            f"    action: pip install pytest",
        ]
    )

    index_first_revision = actual_history_content.find("  - packages:")
    index_second_revision_start = actual_history_content.find(
        "  - packages:", index_first_revision + 1
    )
    second_action = "action: pip install pytest"
    index_second_action = actual_history_content.find(
        second_action, index_second_revision_start
    ) + len(second_action)
    actual_second_revision = actual_history_content[
        index_second_revision_start:index_second_action
    ]
    assert actual_second_revision == expected_second_revision


@pytest.mark.run(order=-10)
def test_conda_env_yaml_pip_install(pip_setup):
    """Test the environment.yml file in detail."""
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

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected


@pytest.mark.run(order=-9)
def test_pip_remove(pip_setup):
    name = pip_setup["name"]
    env_dir = pip_setup["env_dir"]
    channels = pip_setup["channels"]

    pip_remove(name=name, specs=["pytest-cov"], yes=True)

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)
    expected_packages = {
        "conda": {"colorama": "*", "python": "python=3.6"},
        "pip": {"pytest": "pytest==4.0.0"},
    }
    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    expected_log = "pip uninstall pytest-cov"
    assert actual["packages"] == expected_packages
    assert actual["revisions"][-1]["log"] == expected_log
    assert actual["revisions"][-1]["action"] == expected_log

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

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected

    expected_packages_section = "\n".join(
        [
            "packages:",
            "  conda:",
            "    python: python=3.6",
            "    colorama: '*'",
            "  pip:",
            "    pytest: pytest==4.0.0",
            "revisions:",
        ]
    )
    assert expected_packages_section in actual_history_content

    expected_third_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        python: python=3.6",
            "        colorama: '*'",
            "      pip:",
            "        pytest: pytest==4.0.0",
            "    diff:",
            "      pip:",
            "        remove:",
            "        - pytest-cov",
            f"    log: pip uninstall pytest-cov",
            f"    action: pip uninstall pytest-cov",
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
