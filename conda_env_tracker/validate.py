"""Validate inputs to conda_env_tracker."""
import logging
import sys

from conda_env_tracker.env import Environment
from conda_env_tracker.errors import RError, PipInstallError, CondaEnvTrackerRemoteError
from conda_env_tracker.types import PathLike
from conda_env_tracker.gateways.io import EnvIO

logger = logging.getLogger(__name__)


def check_r_base_package(env: Environment) -> None:
    """Make sure r-base is installed to handle installing R packages."""
    dependencies = env.dependencies.get("conda", {})
    if "r-base" not in dependencies:
        package_names = [name for name in dependencies]
        raise RError(
            f'"r-base" not installed.\nFound conda packages:\n{package_names}\n'
            'Must have "r-base" conda installed to install R packages.'
        )


def check_pip(env: Environment) -> None:
    """Make sure pip is installed to handle installing packages with pip install"""
    dependencies = env.dependencies.get("conda", {})
    if "pip" not in dependencies:
        raise PipInstallError("Must have pip installed to install pip packages")


def validate_remote_if_missing(
    env_io: EnvIO, remote_dir: PathLike, yes: bool = False, if_missing: bool = False
):
    """Validate if remote dir exists"""
    try:
        current_remote_dir = env_io.get_remote_dir()
        if not yes and if_missing and remote_dir != current_remote_dir:
            sys.exit(
                f"Current remote directory ({current_remote_dir}) differs from new ({remote_dir}) and [--if-missing] flag was set."
            )
    except CondaEnvTrackerRemoteError:
        pass
