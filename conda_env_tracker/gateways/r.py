"""The conda env tracker interface to installing R packages."""
import logging
from pathlib import Path
import re
import subprocess

from conda_env_tracker.gateways.conda import (
    is_current_conda_env,
    get_conda_activate_command,
)
from conda_env_tracker.gateways.utils import run_command
from conda_env_tracker.errors import RError
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import PathLike

LIST_R_PACKAGES = ";".join(
    (
        "installed_raw <- installed.packages()",
        "installed_df <- as.data.frame(installed_raw, stringsAsFactors=FALSE)",
        'installed <- installed_df[, c("Package", "Version", "Priority")]',
        r'user_installed <- installed[is.na(installed[["Priority"]]), c("Package", "Version"), drop=FALSE]',
        "print(user_installed, row.names=FALSE)",
    )
)
R_COMMAND = "R --quiet --vanilla"


logger = logging.getLogger(__name__)


def get_r_dependencies(name: str) -> dict:
    """Get the R packages and their versions."""
    command = get_shell_command(name=name, r_command=LIST_R_PACKAGES)
    logger.debug(f"Get R dependencies command:\n{command}")
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="UTF-8",
    )
    if process.returncode != 0:
        raise RError(f"Error listing R packages: {process.stderr}")
    return _parse_r_packages(process.stdout)


def r_install(name: str, packages: Packages) -> str:
    """Install R packages."""
    r_command = _combine_r_specs(packages=packages)
    shell_command = _run_r_install(name=name, packages=packages, r_command=r_command)
    r_shell_command = shell_command.split("&&")[-1].strip()
    return r_shell_command


def get_r_install_command(packages: Packages) -> str:
    """Combine the package install commands to form one R command."""
    r_commands = []
    for package in packages:
        r_commands.append(package.spec)
    r_command = ";".join(r_commands)
    return r_command


def r_remove(name: str, package: Packages):
    """Remove r packages.

    shell_command.split will try to split conda activate command from shell command
    """
    r_command = _get_r_remove_command(packages=package)
    shell_command = _run_r_remove(name=name, r_command=r_command)
    r_shell_command = shell_command.split("&&")[-1].strip()
    return r_shell_command


def _run_r_install(name: str, packages: Packages, r_command: str) -> str:
    """Run r install command"""
    command = get_shell_command(name=name, r_command=r_command)
    logger.debug(f"R install command:\n{command}")
    process = run_command(command, error=RError)
    if process.failed or _cannot_install_r_package(process.stderr, packages):
        raise RError(
            f"Error installing R packages:\n{process.stderr}\nenvironment='{name}' and command='{r_command}'."
        )
    return command


def get_r_shell_install_command(packages: Packages) -> str:
    """Get the shell R install command"""
    shell_command = _combine_r_specs(packages=packages)
    return _wrap_r_subprocess_command(shell_command)


def _combine_r_specs(packages: Packages) -> str:
    """Combine the R package install commands into a single R command."""
    return "; ".join(package.spec for package in packages)


def get_r_shell_remove_command(packages: Packages) -> str:
    """Get the shell R install command"""
    shell_command = _get_r_remove_command(packages=packages)
    return _wrap_r_subprocess_command(shell_command)


def export_install_r(packages: Packages) -> str:
    """Create the install.R with R commands that will install all of the packages."""
    install_r = []
    for package in packages:
        install_r.append(package.spec)
    return "\n".join(install_r)


def update_r_environment(name: str, env_dir: PathLike) -> None:
    """Update the R packages in the environment."""
    install_r = Path(env_dir) / "install.R"
    if install_r.exists():
        r_update_command = f'source("{install_r.absolute()}")'
        command = get_shell_command(name=name, r_command=r_update_command)
        logger.debug(f"Update R environment command:\n{command}")
        process = run_command(command, error=RError)
        if process.failed:
            raise RError(f"Error updating R packages in environment:\n{process.stderr}")


def _parse_r_packages(output: str) -> dict:
    """Parse the output from listing the R packages with the actual packages."""
    packages = {}
    lines = output.split("\n")
    for line in lines:
        if (
            line.strip()
            and not line.startswith(">")
            and not line.strip().startswith("Package Version")
        ):
            name, version = line.strip().split()
            spec = name
            packages[name] = Package(name, spec, version)
    return packages


def _cannot_install_r_package(stderr: str, packages: Packages) -> bool:
    for package in packages:
        if (
            f"Warning message:\npackage \u2018{package.name}\u2019 is not available"
            in stderr
        ):
            return True
    return False


def get_shell_command(name: str, r_command: str) -> str:
    """Handle conda env and call R code from command line."""
    commands = []
    if not is_current_conda_env(name=name):
        commands.append(get_conda_activate_command(name=name))
    r_command = _wrap_r_subprocess_command(r_command)
    commands.append(r_command)
    return " && ".join(commands)


def _wrap_r_subprocess_command(command: str) -> str:
    """Allow R code to be run from command line."""
    escaped_command = _escape_command(command)
    return f"{R_COMMAND} -e {escaped_command}"


def _escape_command(string: str) -> str:
    """Any unescaped single quotes must be escaped. Any escaped single quotes must be left alone."""
    if '"' not in string:
        return f'"{string}"'
    escaped_string = re.sub(r'(?<!\\)"', r"\"", string)
    return f'"{escaped_string}"'


def _get_r_remove_command(packages: Packages) -> str:
    """Get r remove command"""
    package_names = []
    for package in packages:
        package_names.append(f'"{package.name}"')
    return f"remove.packages(c({','.join(package_names)}))"


def _run_r_remove(name: str, r_command: str) -> str:
    """Run r remove command"""
    command = get_shell_command(name=name, r_command=r_command)
    logger.debug(f"R remove command:\n{command}")
    process = run_command(command, error=RError)
    if process.failed:
        raise RError(
            f"Error removing R packages:\n{process.stderr}\nenvironment='{name}' and command='{r_command}'."
        )
    return command
