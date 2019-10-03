"""Test pip functionality."""
# pylint: disable=redefined-outer-name
from datetime import date

import oyaml as yaml
import pytest

from conda_env_tracker.gateways import pip
from conda_env_tracker.gateways.conda import CONDA_VERSION, get_dependencies
from conda_env_tracker.main import r_install, r_remove
from conda_env_tracker.gateways.utils import get_platform_name


@pytest.fixture(scope="module")
def r_setup(r_end_to_end_setup):
    """Doing pip install to setup for testing history and conda env yaml files."""
    env = r_install(
        name=r_end_to_end_setup["name"],
        package_names=["jsonlite", "praise"],
        commands=[
            'library("devtools"); install_version("jsonlite", version="1.2")',
            'install.packages("praise")',
        ],
        yes=True,
    )
    r_end_to_end_setup["env"] = env
    return r_end_to_end_setup


@pytest.mark.run(order=-14)
def test_history_r_install(r_setup):
    """Test the history.yaml in detail."""
    # pylint: disable=line-too-long
    name = r_setup["name"]
    env = r_setup["env"]
    env_dir = r_setup["env_dir"]
    channels = r_setup["channels"]

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    expected_packages = {
        "conda": {"r-base": "*", "r-devtools": "*"},
        "r": {
            "jsonlite": 'library("devtools"); install_version("jsonlite",version="1.2")',
            "praise": 'install.packages("praise")',
        },
    }

    expected_log = (
        r'R --quiet --vanilla -e "library(\"devtools\"); '
        r"install_version(\"jsonlite\",version=\"1.2\"); "
        r"install.packages(\"praise\")"
    )

    expected_action = (
        r'R --quiet --vanilla -e "library(\"devtools\"); '
        r"install_version(\"jsonlite\",version=\"1.2\",date=\"2019-01-01\"); "
        r'library(\"devtools\"); install_mran(\"praise\",version=\"1.0.0\",date=\"2019-01-01\")"'
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
    assert actual["revisions"][-1]["action"] == expected_action
    for i in range(len(actual["revisions"])):
        for key, val in expected_debug[i].items():
            if key == "timestamp":
                assert actual["revisions"][i]["debug"][key].startswith(val)
            else:
                assert actual["revisions"][i]["debug"][key] == val

    dependencies = env.dependencies

    expected_history = [
        f"name: {name}",
        f"id: {env.history.id}",
        "history-file-version: '1.0'",
        "channels:",
    ]
    for channel in channels:
        expected_history.append(f"  - {channel}")
    expected_history_start = "\n".join(
        expected_history
        + [
            "packages:",
            "  conda:",
            "    r-base: '*'",
            "    r-devtools: '*'",
            "  r:",
            '    jsonlite: library("devtools"); install_version("jsonlite",version="1.2")',
            '    praise: install.packages("praise")',
            "revisions:",
            "  - packages:",
            "      conda:",
            "        r-base: '*'",
            "        r-devtools: '*'",
            "    diff:",
            "      conda:",
            "        upsert:",
            f"        - r-base={dependencies['conda']['r-base'].version}",
            f"        - r-devtools={dependencies['conda']['r-devtools'].version}",
            "    log: conda create --name r_end_to_end_test r-base r-devtools --override-channels",
            "      --strict-channel-priority --channel r",
            "      --channel defaults",
            "    action: conda create --name r_end_to_end_test r-base",
        ]
    )
    expected_second_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        r-base: '*'",
            "        r-devtools: '*'",
            "      r:",
            '        jsonlite: library("devtools"); install_version("jsonlite",version="1.2")',
            '        praise: install.packages("praise")',
            "    diff:",
            "      r:",
            "        upsert:",
            f"        - jsonlite",
            f"        - praise",
            r'    log: R --quiet --vanilla -e "library(\"devtools\"); install_version(\"jsonlite\",version=\"1.2\");',
            r"      install.packages(\"praise\")",
            r'    action: R --quiet --vanilla -e "library(\"devtools\"); install_version(\"jsonlite\",version=\"1.2\");',
            r"      install.packages(\"praise\")",
        ]
    )
    index_first_action = actual_history_content.find(
        "action: conda create --name r_end_to_end_test r-base"
    ) + len("action: conda create --name r_end_to_end_test r-base")
    actual_history_start = actual_history_content[:index_first_action]
    assert actual_history_start == expected_history_start

    index_second_revision_start = actual_history_content.find(
        "  - packages:", index_first_action
    )
    index_second_debug = actual_history_content.find(
        "debug:", index_second_revision_start
    )
    actual_second_revision = actual_history_content[
        index_second_revision_start:index_second_debug
    ].rstrip()
    assert actual_second_revision == expected_second_revision


@pytest.mark.run(order=-13)
def test_conda_env_yaml_r_install(r_setup):
    """Test the environment.yml file in detail."""
    name = r_setup["name"]
    env_dir = r_setup["env_dir"]
    channels = r_setup["channels"]

    packages = get_dependencies(name=name)
    conda_packages = packages["conda"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_conda_packages = [
        "  - r-base=" + conda_packages["r-base"].version,
        "  - r-devtools=" + conda_packages["r-devtools"].version,
    ]

    expected = "\n".join(expected_start + expected_conda_packages) + "\n"

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected

    install_r = "\n".join(
        [
            'library("devtools"); install_version("jsonlite", version="1.2")',
            'install.packages("praise")',
        ]
    )

    actual_install_r = (env_dir / "install.R").read_text()
    print(actual_install_r)
    assert actual_install_r == install_r


@pytest.mark.run(order=-12)
def test_r_remove_package(r_setup):
    # pylint: disable=too-many-locals
    name = r_setup["name"]
    env_dir = r_setup["env_dir"]
    channels = r_setup["channels"]

    r_remove(name=name, specs=["praise"], yes=True)

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)
    expected_packages = {
        "conda": {"r-base": "*", "r-devtools": "*"},
        "r": {
            "jsonlite": 'library("devtools"); install_version("jsonlite", version="1.2")'
        },
    }
    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)
    remove_command = r"remove.packages(c(\"praise\"))"
    expected_log = f'R --quiet --vanilla -e "{remove_command}"'

    assert actual["packages"] == expected_packages
    assert actual["revisions"][-1]["log"] == expected_log
    assert actual["revisions"][-1]["action"] == expected_log

    packages = get_dependencies(name=name)
    conda_packages = packages["conda"]

    expected_start = [f"name: {name}", "channels:"]
    for channel in channels + ["nodefaults"]:
        expected_start.append(f"  - {channel}")
    expected_start.append("dependencies:")

    expected_conda_packages = [
        "  - r-base=" + conda_packages["r-base"].version,
        "  - r-devtools=" + conda_packages["r-devtools"].version,
    ]

    expected = "\n".join(expected_start + expected_conda_packages) + "\n"

    actual = (env_dir / "environment.yml").read_text()
    print(actual)
    assert actual == expected

    install_r = "\n".join(
        ['library("devtools"); install_version("jsonlite", version="1.2")']
    )

    actual_install_r = (env_dir / "install.R").read_text()
    print(actual_install_r)
    assert actual_install_r == install_r

    expected_packages_section = "\n".join(
        [
            "packages:",
            "  conda:",
            "    r-base: '*'",
            "    r-devtools: '*'",
            "  r:",
            '    jsonlite: library("devtools"); install_version("jsonlite",version="1.2")',
            "revisions:",
        ]
    )
    assert expected_packages_section in actual_history_content

    expected_third_revision = "\n".join(
        [
            "  - packages:",
            "      conda:",
            "        r-base: '*'",
            "        r-devtools: '*'",
            "      r:",
            '        jsonlite: library("devtools"); install_version("jsonlite",version="1.2")',
            "    diff:",
            "      r:",
            "        remove:",
            "        - praise",
            rf'    log: R --quiet --vanilla -e "remove.packages(c(\"praise\"))"',
            rf'    action: R --quiet --vanilla -e "remove.packages(c(\"praise\"))"',
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
