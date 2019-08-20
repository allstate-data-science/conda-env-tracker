"""Doing pip installs/uninstalls into conda_env_tracker conda environment.

Note that setting a default index url allows for different default mirrors,
which may be useful in corporate firewalls.
"""

import logging
import subprocess
from typing import Optional, Union

from conda_env_tracker.gateways.conda import (
    get_conda_activate_command,
    get_dependencies,
    is_current_conda_env,
)
from conda_env_tracker.errors import PipRemoveError, PipInstallError
from conda_env_tracker.gateways.utils import run_command
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import ListLike

PIP_DEFAULT_INDEX_URL = "https://pypi.org/simple"

logger = logging.getLogger(__name__)


def pip_install(
    name: str,
    packages: Packages,
    index_url: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL,
) -> None:
    """Pip installing packages."""
    commands = []
    if not is_current_conda_env(name):
        commands.append(get_conda_activate_command(name=name))
    commands.append(get_pip_install_command(packages, index_url))
    command = " && ".join(commands)
    logger.debug(f"Pip install command: {command}")
    install = subprocess.run(
        command, shell=True, stderr=subprocess.PIPE, encoding="UTF-8"
    )
    if install.returncode != 0:
        raise PipInstallError(
            f"Pip install {[package.spec for package in packages]} failed with message: {install.stderr}"
        )


def pip_custom_install(name: str, package: Package):
    """Pip installing packages with custom urls"""
    commands = []
    if not is_current_conda_env(name):
        commands.append(get_conda_activate_command(name=name))
    pip_command = get_pip_custom_install_command(spec=package.spec)
    logger.debug(f"Pip install command: {pip_command}")
    commands.append(pip_command)
    command = " && ".join(commands)
    install = subprocess.run(
        command, shell=True, stderr=subprocess.PIPE, encoding="UTF-8"
    )
    if install.returncode != 0:
        raise PipInstallError(
            f"Pip install {package.name} with custom url [{package.spec}] failed with message: {install.stderr}"
        )


def get_pip_install_command(
    packages: Packages, index: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL
) -> str:
    """Get the command to pip install the package."""
    index_command = _get_index_command(index)
    return (
        f"pip install {' '.join(package.spec for package in packages)} {index_command}"
    )


def get_pip_remove_command(packages: Packages, yes) -> str:
    """Get the command to pip uninstall the package"""
    uninstall_cmd = f"pip uninstall {' '.join(package.name for package in packages)}"
    if yes:
        uninstall_cmd += " --yes"
    return uninstall_cmd


def get_pip_custom_install_command(spec: str) -> str:
    """Get the custom pip install command"""
    return f"pip install {spec}"


def get_pip_version(name: str) -> Optional[str]:
    """Check for the version of pip (if installed)."""
    if is_current_conda_env(name):
        import pip

        return pip.__version__
    dependencies = get_dependencies(name=name)
    return dependencies["conda"].get("pip", Package(name="pip")).version


def _get_index_command(index: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL) -> str:
    """Pip can handle multiple index urls which may be useful."""
    if isinstance(index, str):
        return f"--index-url {index}"
    commands = ["--index-url"]
    for i, url in enumerate(index):
        if i != 0:
            commands.append("--extra-index-url")
        commands.append(url)
    return " ".join(commands)


def pip_remove(name: str, packages: Packages, yes):
    """Pip uninstall package, can handle custom package removal"""
    commands = []
    if not is_current_conda_env(name):
        commands.append(get_conda_activate_command(name=name))
    commands.append(get_pip_remove_command(packages, yes))
    command = " && ".join(commands)
    logger.debug(f"Pip remove command: {command}")
    run_command(command, error=PipRemoveError)
