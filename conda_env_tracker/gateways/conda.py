"""External conda functionality for conda_env_tracker."""

import logging
import os
from pathlib import Path
import subprocess
from typing import Union

from conda_env_tracker.channels import Channels
from conda_env_tracker.errors import CondaEnvTrackerCondaError
from conda_env_tracker.gateways.utils import run_command
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import ListLike, PathLike

logger = logging.getLogger(__name__)

MINIMUM_CONDA_VERSION = "4.5"


def init() -> str:
    """Check conda version."""
    completed_process = subprocess.run(
        "conda --version",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )
    process_code = completed_process.returncode
    if process_code == 0:
        conda_version = completed_process.stdout.rstrip().split(" ")[1]
    else:
        raise CondaEnvTrackerCondaError(
            "Error checking conda version. Maybe you haven't installed anaconda/miniconda?"
            f"\nError: {completed_process.stderr}"
        )
    if conda_version < MINIMUM_CONDA_VERSION:
        raise CondaEnvTrackerCondaError(
            f"Need conda>={MINIMUM_CONDA_VERSION}, but found conda={conda_version}."
            ' Please run "conda update -n base conda".'
        )
    logger.info(f"Using conda version {conda_version}")
    return conda_version


CONDA_VERSION = init()


def get_conda_bin_path() -> Path:
    """Find the path to the conda binary."""
    conda_exe_path = os.environ.get("CONDA_EXE")
    if conda_exe_path:
        return Path(conda_exe_path).parent
    completed_process = subprocess.run(
        "which conda",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )
    process_code = completed_process.returncode
    if process_code != 0:
        raise CondaEnvTrackerCondaError(
            "CondaEnvTracker requires an anaconda/miniconda install"
        )
    return Path(completed_process.stdout.strip()).parent


def get_all_existing_environment() -> ListLike:
    """Check if environment with name already exist"""
    env_list = []
    proc = subprocess.run(
        "conda env list",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )
    env_info = proc.stdout.rstrip().split("\n")
    for line in env_info:
        if not line.startswith("#"):
            env_name = line.split()[0]
            env_list.append(env_name)
    return env_list


def get_dependencies(name: str) -> dict:
    """Get the information about pip and conda packages in the environment using `conda list`.

    Package information includes: name and version
    """
    completed_process = subprocess.run(
        f"conda list --name {name}",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )
    if completed_process.returncode != 0:
        error_message = completed_process.stderr.strip()
        raise CondaEnvTrackerCondaError(error_message)
    lines = completed_process.stdout.strip().split("\n")
    dependencies = {"conda": {}}
    for line in lines:
        if not line.startswith("#"):
            dep = line.strip().split()
            name = dep[0]
            spec = name
            version = dep[1]
            if dep[-1] in ["pip", "pypi"]:
                dependencies["pip"] = dependencies.get("pip", {})
                dependencies["pip"][name] = Package(name, spec, version)
            else:
                build = dep[2]
                dependencies["conda"][name] = Package(name, spec, version, build)

    return dependencies


def get_conda_channels() -> ListLike:
    """Get the conda channels and their priority"""
    completed_process = subprocess.run(
        "conda config --get channels",
        stdout=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )
    channels_list = completed_process.stdout.rstrip().split("\n")
    conda_channels = []
    for channel in channels_list:
        conda_channels.append(channel.split("'")[1])
    conda_channels.reverse()
    return conda_channels


def delete_conda_environment(name: str) -> None:
    """Delete conda environment"""
    if os.environ["CONDA_DEFAULT_ENV"] == name:
        raise CondaEnvTrackerCondaError(
            f'Must run "conda deactivate" before removing or rebuilding the {name} environment.'
        )
    subprocess.run(f"conda env remove -y --name {name}", shell=True)


def conda_create(
    name: str,
    packages: Packages,
    channels: ListLike = None,
    yes: bool = False,
    strict_channel_priority: bool = True,
) -> str:
    """Create a conda environment."""
    create_cmd = get_conda_create_command(
        name,
        packages,
        channels,
        yes=yes,
        strict_channel_priority=strict_channel_priority,
    )
    logger.debug(f"Conda creation command:\n{create_cmd}")
    run_command(create_cmd, error=CondaEnvTrackerCondaError)
    return create_cmd


def conda_install(
    name: str, packages: Packages, channel_command: str, yes: bool = False
) -> str:
    """Conda install the packages"""
    install_cmd = get_conda_install_command(name, packages, yes)
    run_command(f"{install_cmd} {channel_command}", error=CondaEnvTrackerCondaError)
    return install_cmd


def conda_remove(
    name: str, packages: Packages, channel_command: str, yes: bool = False
) -> str:
    """Conda remove the packages"""
    remove_cmd = get_conda_remove_command(name, packages, yes=yes)
    run_command(f"{remove_cmd} {channel_command}", error=CondaEnvTrackerCondaError)
    return remove_cmd


def conda_update_all(
    name: str, channels: str, packages: Packages = (), yes: bool = False
) -> str:
    """Conda update all packages."""
    update_cmd = get_conda_update_all_command(name, packages, yes=yes)
    run_command(f"{update_cmd} {channels}", error=CondaEnvTrackerCondaError)
    return update_cmd


def get_conda_create_command(
    name: str,
    packages: Packages,
    channels: ListLike = None,
    yes: bool = False,
    strict_channel_priority: bool = True,
) -> str:
    """Create the conda create command"""
    command = ["conda", "create"]
    if yes:
        command.append("-y")
    command.extend(["--name", name])
    command.append(_join_packages(packages))
    if channels:
        channel_command = Channels(channels).create_channel_command(
            strict_channel_priority=strict_channel_priority
        )
        command.append(channel_command)
    create_cmd = " ".join(command)
    return create_cmd


def get_conda_install_command(
    name: str, packages: Union[Packages, ListLike], yes: bool = False
) -> str:
    """Create the conda install command."""
    packages_cmd = _join_packages(packages)
    if yes:
        prefix_cmd = f"conda install -y --name {name} {packages_cmd}"
    else:
        prefix_cmd = f"conda install --name {name} {packages_cmd}"
    return prefix_cmd


def get_conda_update_all_command(
    name: str, packages: Packages = (), yes: bool = False
) -> str:
    """Create the conda update command."""
    packages_cmd = _join_packages(packages)
    if packages:
        packages_cmd = " " + packages_cmd
    if yes:
        prefix_cmd = f"conda update --all -y --name {name}{packages_cmd}"
    else:
        prefix_cmd = f"conda update --all --name {name}{packages_cmd}"
    return prefix_cmd


def get_conda_remove_command(name: str, packages: Packages, yes: bool = False) -> str:
    """Create the conda remove command"""
    packages_cmd = _join_packages(packages)
    if yes:
        prefix_cmd = f"conda remove -y --name {name} {packages_cmd}"
    else:
        prefix_cmd = f"conda remove --name {name} {packages_cmd}"
    return prefix_cmd


def _join_packages(packages: Packages) -> str:
    """Join a list of package specs."""
    return " ".join(package.spec for package in packages)


def update_conda_environment(env_dir: PathLike) -> None:
    """Update the given environment with using environment yaml file.
    This file only contains packages the user has specifically asked for
    and does not contain dependencies.
    """
    env_dir = Path(env_dir)
    env_file = _get_env_file(env_dir)
    run_command(
        f'conda env update --prune --file "{env_file}"', error=CondaEnvTrackerCondaError
    )


def _get_env_file(env_dir: Path) -> Path:
    """Get the environment file. This file only contains packages the 
    user has specifically asked for and does not contain dependencies."""
    env_file = env_dir / "conda-env.yaml"
    if env_file.exists():
        return env_file
    raise CondaEnvTrackerCondaError(
        f"No environment file to update from in {env_dir}.\n"
        "Someone may need to push to this remote or recover the lost file in some other way."
    )


def get_active_conda_env_name() -> str:
    """Returns the name of the currently active conda environment"""
    process = subprocess.run(
        "echo $CONDA_DEFAULT_ENV", shell=True, stdout=subprocess.PIPE, encoding="UTF-8"
    )
    return process.stdout.strip()


def is_current_conda_env(name: str) -> bool:
    """A function that checks if a specific conda env is activated"""
    active_env_name = os.environ.get("CONDA_DEFAULT_ENV", "").strip()
    return name == active_env_name


def get_conda_activate_command(name):
    """Source the conda shell functions to be able to use `conda activate`.

    This path has been stable from version 4.4 to 4.6 of conda.
    """
    conda_bin_path = get_conda_bin_path()
    conda_functions_script = conda_bin_path.parent / "etc" / "profile.d" / "conda.sh"
    return f"source {conda_functions_script} && conda activate {name}"
