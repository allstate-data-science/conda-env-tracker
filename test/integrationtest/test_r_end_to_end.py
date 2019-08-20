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
    r_install(
        name=r_end_to_end_setup["name"],
        package_names=["jsonlite", "praise"],
        commands=[
            'library("devtools"); install_version("jsonlite", version="1.2")',
            'install.packages("praise")',
        ],
        yes=True,
    )
    return r_end_to_end_setup


@pytest.mark.run(order=-14)
def test_history_r_install(r_setup):
    """Test the history.yaml in detail."""
    # pylint: disable=line-too-long
    name = r_setup["name"]
    env_dir = r_setup["env_dir"]
    channels = r_setup["channels"]

    history_file = env_dir / "history.yaml"
    actual_history_content = history_file.read_text()
    print(actual_history_content)

    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)

    expected_action = 'R --quiet --vanilla -e \'library("devtools"); install_version("jsonlite", version="1.2"); install.packages("praise")\''

    expected_packages = {
        "conda": {"r-base": "*", "r-devtools": "*"},
        "r": {"jsonlite": "1.2", "praise": "*"},
    }
    expected_log = 'R --quiet --vanilla -e \'library("devtools"); install_version("jsonlite", version="1.2"); install.packages("praise")\''
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
    assert actual["actions"][-1] == expected_action
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
            "    r-base: '*'",
            "    r-devtools: '*'",
            "  r:",
            "    jsonlite: '1.2'",
            "    praise: '*'",
            "logs:",
            "  - conda create --name end_to_end_test r-base r-devtools --override-channels",
            "    --strict-channel-priority",
            "    --channel r --channel defaults",
            "    main",
            '  - R --quiet --vanilla -e \'library("devtools"); install_version("jsonlite", version="1.2");',
            '    install.packages("praise")\'',
            "actions:",
            f"  - conda create --name {name} r-base",
        ]
    )
    end = actual_history_content.rfind("r-base") + len("r-base")
    actual_history_start = actual_history_content[:end]
    assert actual_history_start == expected_history_start


@pytest.mark.run(order=-13)
def test_conda_env_yaml_r_install(r_setup):
    """Test the conda-env.yaml file in detail."""
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

    actual = (env_dir / "conda-env.yaml").read_text()
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
    name = r_setup["name"]
    env_dir = r_setup["env_dir"]
    channels = r_setup["channels"]

    history_file = env_dir / "history.yaml"
    r_remove(name=name, specs=["praise"], yes=True)
    actual_history_content = history_file.read_text()
    print(actual_history_content)
    expected_packages = {
        "conda": {"r-base": "*", "r-devtools": "*"},
        "r": {"jsonlite": "1.2"},
    }
    actual = yaml.load(actual_history_content, Loader=yaml.FullLoader)
    remove_command = 'remove.packages(c("praise"))'
    expected_log = f"R --quiet --vanilla -e '{remove_command}'"

    assert actual["packages"] == expected_packages
    assert actual["logs"][-1] == expected_log
    assert actual["actions"][-1] == expected_log

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

    actual = (env_dir / "conda-env.yaml").read_text()
    print(actual)
    assert actual == expected

    install_r = "\n".join(
        ['library("devtools"); install_version("jsonlite", version="1.2")']
    )

    actual_install_r = (env_dir / "install.R").read_text()
    print(actual_install_r)
    assert actual_install_r == install_r
