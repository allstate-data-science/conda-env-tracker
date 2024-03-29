"""Test the r functionality."""
import os
from pathlib import Path
import subprocess

import pytest

from conda_env_tracker.gateways import r
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker import errors

CONDA_SH_PATH = (
    Path(os.environ["CONDA_EXE"]).parent.parent / "etc" / "profile.d" / "conda.sh"
)


def test_export_install_r_single_package():
    packages = Packages(
        Package(
            "jsonlite", 'library("devtools"); install_version("jsonlite",version="1.6")'
        )
    )
    actual = r.export_install_r(packages)
    expected = 'library("devtools"); install_version("jsonlite",version="1.6")'
    assert actual == expected


def test_export_install_r_multiple_packages():
    packages = Packages(
        [
            Package(
                "jsonlite",
                'library("devtools"); install_version("jsonlite",version="1.6")',
            ),
            Package(
                "praise",
                'library("devtools"); install_version("praise",version="1.0.0")',
            ),
        ]
    )
    actual = r.export_install_r(packages)
    expected = "\n".join(
        [
            'library("devtools"); install_version("jsonlite",version="1.6")',
            'library("devtools"); install_version("praise",version="1.0.0")',
        ]
    )
    assert actual == expected


def test_export_install_r_multiple_installs():
    packages = Packages(
        [
            Package(
                "jsonlite",
                'library("devtools"); install_version("jsonlite",version="1.6")',
            ),
            Package(
                "praise",
                'library("devtools"); install_version("praise",version="1.0.0")',
            ),
        ]
    )
    actual = r.export_install_r(packages)
    expected = "\n".join(
        [
            'library("devtools"); install_version("jsonlite",version="1.6")',
            'library("devtools"); install_version("praise",version="1.0.0")',
        ]
    )
    assert actual == expected


def test_export_install_r_no_r_packages():
    actual = r.export_install_r(Packages())
    expected = ""
    assert actual == expected


def test_parse_r_packages(mocker):
    stdout = f"""> {r.LIST_R_PACKAGES}
          Package Version
       checkpoint   0.4.5
         jsonlite     1.6
           praise   1.0.0
             utf8   1.1.4
> 
> 
"""
    run_mock = mocker.patch("conda_env_tracker.gateways.r.subprocess.run")
    run_mock.configure_mock(
        **{"return_value.stdout": stdout, "return_value.returncode": 0}
    )

    actual = r.get_r_dependencies(name="env_name")

    escaped_list_r_packages = r.LIST_R_PACKAGES.replace('"', r"\"")

    expected_command = (
        f"source {CONDA_SH_PATH} && "
        "conda activate env_name && "
        f'R --quiet --vanilla -e "{escaped_list_r_packages}"'
    )

    run_mock.assert_called_once_with(
        expected_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )

    expected = {
        "checkpoint": Package("checkpoint", "checkpoint", "0.4.5"),
        "jsonlite": Package("jsonlite", "jsonlite", "1.6"),
        "praise": Package("praise", "praise", "1.0.0"),
        "utf8": Package("utf8", "utf8", "1.1.4"),
    }

    assert actual == expected


def test_update_r_environment(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(
        **{"return_value.stderr": "stderr", "return_value.failed": False}
    )
    env_dir = Path(__file__).parent / "tmp"
    if not env_dir.exists():
        env_dir.mkdir()
    install_r = env_dir / "install.R"
    install_r.touch()

    r.update_r_environment(name="env_name", env_dir=env_dir)

    expected_command = (
        f"source {CONDA_SH_PATH} && "
        "conda activate env_name && "
        rf'R --quiet --vanilla -e "source(\"{install_r.absolute()}\")"'
    )

    run_mock.assert_called_once_with(expected_command, error=errors.RError)

    install_r.unlink()
    env_dir.rmdir()


def test_update_r_environment_error(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(
        **{"return_value.stderr": "stderr", "return_value.failed": True}
    )
    env_dir = Path(__file__).parent / "tmp"
    if not env_dir.exists():
        env_dir.mkdir()
    install_r = env_dir / "install.R"
    install_r.touch()

    with pytest.raises(errors.RError) as err:
        r.update_r_environment(name="env_name", env_dir=env_dir)

    assert str(err.value) == "Error updating R packages in environment:\nstderr"

    install_r.unlink()
    env_dir.rmdir()


def test_r_install_error(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(
        **{"return_value.stderr": "stderr", "return_value.failed": True}
    )
    expected_command = "install.packages('jsonlite')"
    with pytest.raises(errors.RError) as err:
        r.r_install(
            name="env_name", packages=Packages(Package("jsonlite", expected_command))
        )
    assert str(err.value) == (
        "Error installing R packages:\nstderr\n"
        f"environment='env_name' and command='{expected_command}'."
    )
