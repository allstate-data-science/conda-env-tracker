"""Handle package specifications from users and convert to what is expected by conda_env_tracker."""

from conda_env_tracker.errors import CondaEnvTrackerPackageNameError, RError
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import ListLike


def process_specs(specs: ListLike, check_custom: bool = False) -> Packages:
    """Cleaning all package specs and converting to a package class for conda and pip packages.

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


def process_r_specs(package_names: ListLike, commands: ListLike) -> Packages:
    """Generate the install commands for R packages and return as the package spec."""
    if len(package_names) != len(commands):
        raise RError(
            f"Must have same number of package names ({len(package_names)}) and install commands ({len(commands)})."
        )
    packages = Packages()
    for package_name, command in zip(package_names, commands):
        packages.append(Package(package_name, spec=command))
    return packages
