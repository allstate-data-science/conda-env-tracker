"""Utility functions for interacting with jupyter."""

import logging
import subprocess

from conda_env_tracker.gateways.conda import (
    is_current_conda_env,
    get_conda_activate_command,
)
from conda_env_tracker.errors import JupyterKernelInstallError
from conda_env_tracker.packages import Packages
from conda_env_tracker.utils import prompt_yes_no

logger = logging.getLogger(__name__)


def jupyter_kernel_install_query(name: str, packages: Packages):
    """A function to install conda env as jupyter kernel if user agrees"""
    if any(pkg.name.startswith("jupyter") for pkg in packages):
        try:
            if _jupyter_kernel_exists(name=name):
                logger.debug(f"{name} is already installed as a jupyter kernel")
            else:
                if prompt_yes_no(
                    prompt_msg=f"Would you like to register {name} as a "
                    "jupyter kernel available from another environment"
                ):
                    _install_conda_jupyter_kernel(name=name)
        except JupyterKernelInstallError as err:
            logger.debug(f"Error while installing jupyter kernel: {str(err)}")


def _install_conda_jupyter_kernel(name):
    """Function to install conda env as jupyter kernel"""
    command = _ensure_correct_conda_env_activated(
        name=name, command=f"python -m ipykernel install --name {name} --user"
    )
    setup = subprocess.run(
        command, shell=True, stderr=subprocess.PIPE, encoding="UTF-8"
    )
    if setup.returncode != 0:
        raise JupyterKernelInstallError(setup.stderr)


def _jupyter_kernel_exists(name: str):
    """A function to determine whether a jupyter kernel already exists with this name"""
    command = _ensure_correct_conda_env_activated(
        name=name, command="jupyter kernelspec list"
    )
    completed_process = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, encoding="UTF-8"
    )
    if completed_process.returncode != 0:
        raise JupyterKernelInstallError(completed_process.stderr)
    jupyter_kernel_list = completed_process.stdout.rstrip().split("\n")
    for row in jupyter_kernel_list[1:]:
        if row.split()[0] == name:
            return True
    return False


def _ensure_correct_conda_env_activated(name: str, command: str):
    """If the current conda environment is not the named conda environment, then activate first."""
    if not is_current_conda_env(name):
        return get_conda_activate_command(name=name) + " && " + command
    return command
