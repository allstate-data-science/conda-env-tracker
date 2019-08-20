"""Utility functions that get information from system."""
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict

from invoke import run

from conda_env_tracker.errors import (
    NotGitRepoError,
    CondaEnvTrackerHistoryNotFoundError,
)
from conda_env_tracker.packages import Packages

logger = logging.getLogger(__name__)


def infer_remote_dir(check_history_exists: bool = True) -> str:
    """Find the remote directory in the current directory or git root directory."""
    remote_dir = Path() / ".cet"
    if remote_dir.is_dir() and (remote_dir / "history.yaml").exists():
        return remote_dir
    process = subprocess.run(
        "git rev-parse --show-toplevel;",
        shell=True,
        stdout=subprocess.PIPE,
        encoding="UTF-8",
    )
    git_root_dir = Path(process.stdout.strip())
    if not git_root_dir.is_dir():
        raise NotGitRepoError(
            "Current directory has no '.cet/' directory and is not in a git repo."
        )
    remote_dir = git_root_dir / ".cet"
    history_file = remote_dir / "history.yaml"
    if not check_history_exists or history_file.exists():
        return remote_dir
    raise CondaEnvTrackerHistoryNotFoundError(
        f"history.yaml file not found in {remote_dir}"
    )


def get_platform_name() -> str:
    """Get the name of the operating system in the conda style, excluding the 32/64 at the end."""
    platform = sys.platform.lower()
    if platform == "darwin":
        return "osx"
    if platform.startswith("win"):
        return "win"
    return "linux"


def run_command(command: str, error):
    """Run a shell command."""
    process = run(command, pty=True, warn=True)
    if _user_did_not_complete_command(process.stdout):
        sys.exit(0)
    if process.failed and (
        "KeyboardInterrupt" in process.stdout or "KeyboardInterrupt" in process.stderr
    ):
        sys.exit(0)
    elif process.failed:
        logger.error(command)
        raise error(process.stderr)
    return process


def _user_did_not_complete_command(stdout: str) -> bool:
    """If the command asks for user input to continue, then check if they user answered 'n'."""
    start = stdout.rfind("?") + 1
    if start == 0:
        return False
    end = stdout.find("\n", start)
    return stdout[start:end].strip().lower().startswith("n")


def print_package_list(packages: Dict[str, Packages]) -> None:
    """This function prints each of the packages in the environment"""
    for source, list_of_pkgs in packages.items():
        print(f"#{source}:")
        print(f"#   PACKAGE -> SPEC -> VERSION")
        for pkg in list_of_pkgs:
            print(f"    {pkg.name} -> {pkg.spec} -> {pkg.version}")
