"""Validate inputs to conda_env_tracker."""
from itertools import zip_longest
import logging

from conda_env_tracker.env import Environment
from conda_env_tracker.errors import (
    RError,
    PipInstallError,
    CondaEnvTrackerPackageNameError,
)
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import ListLike

logger = logging.getLogger(__name__)


def clean_specs(specs: ListLike, check_custom: bool = False) -> Packages:
    """Cleaning all package specs and converting to a package class.

    All package names for both pip and conda can be used with lowercase only. Conda automatically converts to lowercase.
    This allows our internal dictionaries that use package names as keys to be consistent with `conda list`.
    """
    cleaned = Packages()
    for spec in specs:
        if check_custom and "/" in spec:
            raise CondaEnvTrackerPackageNameError(
                f"Found illegal character in package name or spec: '{spec}'.\n"
                "Maybe you want to use --custom which requires package name and custom url, e.g.\n"
                f"'cet pip install package_name --custom package_url'"
            )
        cleaned.append_spec(spec.lower())
    return cleaned


def clean_r_specs(package_names: ListLike, commands: ListLike) -> Packages:
    """Cleaning all R package specs and converting to a package class."""
    packages = Packages()
    for package_name, command in zip_longest(package_names, commands):
        if not package_name or not command:
            raise RError(
                (
                    "Must have same number of R package names and install commands.\n"
                    f"Package names: {package_names}\n"
                    f"and install commands: {commands}"
                )
            )
        packages.append(Package(package_name, command))
    return packages


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
