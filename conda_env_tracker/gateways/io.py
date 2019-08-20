"""Class to perform input output operations"""

import logging
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Optional

import oyaml as yaml

import conda_env_tracker.utils
import conda_env_tracker.gateways.utils
from conda_env_tracker.errors import CondaEnvTrackerRemoteError, WindowsError
from conda_env_tracker.history import History
from conda_env_tracker.types import PathLike

logger = logging.getLogger(__name__)

USER_CET_DIR = Path.home() / ".cet"
USER_ENVS_DIR = USER_CET_DIR / "envs"
SHELL_FILE = Path(__file__).parent.parent / "shell" / "cet-auto.sh"


def init(yes: bool = False) -> None:
    """Make link to cet command line tool and add path to bash config file."""
    cet_package_cli = Path(sys.exec_prefix) / "bin" / "cet"
    if not USER_CET_DIR.exists():
        USER_CET_DIR.mkdir()
    cet_user_cli = USER_CET_DIR / "cet"
    if cet_user_cli.exists():
        cet_user_cli.unlink()
    os.symlink(cet_package_cli, cet_user_cli)
    bash_config_line = f'\nexport PATH="$PATH:{cet_user_cli.parent}"\n'
    _add_line_to_bash_config_file(
        bash_config_line,
        prompt="Append cet command line tool to PATH in {file}",
        yes=yes,
    )


def link_auto() -> None:
    """Copy the auto shell script to the user cet dir"""
    user_shell_file = USER_CET_DIR / SHELL_FILE.name
    package_script = SHELL_FILE.read_text()
    if user_shell_file.exists():
        user_script = user_shell_file.read_text()
        if package_script != user_script and conda_env_tracker.utils.prompt_yes_no(
            f"Overwrite {user_shell_file} with package shell script"
        ):
            user_shell_file.unlink()
            os.symlink(SHELL_FILE, user_shell_file)
    else:
        if user_shell_file.is_symlink():
            user_shell_file.unlink()
        os.symlink(SHELL_FILE, user_shell_file)


def add_auto_to_bash_config_file(
    activate: bool = False, sync: bool = False, yes: bool = False
) -> None:
    """Source the cet-auto.sh in the bash profile or bashrc"""
    source_auto = f"\nsource {Path.home()}/.cet/cet-auto.sh\n"
    _add_line_to_bash_config_file(source_auto, prompt="Add cet auto in {file}", yes=yes)
    if activate:
        activate_auto = "export CET_ACTIVATE_AUTO=0\n"
        _add_line_to_bash_config_file(
            activate_auto,
            prompt="Add environment variable in {file} to run conda activate without asking",
            yes=yes,
        )
    if sync:
        sync_auto = "export CET_SYNC_AUTO=0\n"
        _add_line_to_bash_config_file(
            sync_auto,
            prompt="Add environment variable in {file} to run cet sync without asking",
            yes=yes,
        )


def _add_line_to_bash_config_file(line: str, prompt: str, yes: bool = False) -> None:
    platform = conda_env_tracker.gateways.utils.get_platform_name()
    if platform == "linux":
        file_name = ".bashrc"
    elif platform == "osx":
        file_name = ".bash_profile"
    else:  # windows
        raise WindowsError("Windows is unsupported at this time")
    file = Path.home() / file_name
    _add_line(file, line=line, prompt=prompt, yes=yes)


def _add_line(file: Path, line: str, prompt: str, yes: bool = False) -> None:
    if file.exists():
        content = file.read_text()
    else:
        content = ""
    if line not in content and (
        yes or conda_env_tracker.utils.prompt_yes_no(prompt.format(file=file.name))
    ):
        content = content + line
        if file.exists():
            previous_modify_time = os.path.getmtime(file)
        else:
            previous_modify_time = 0
        file.write_text(content)
        if time.time() - previous_modify_time > 300:
            logger.info(
                f'To finish initialization start a new terminal session or run "source ~/{file.name}".'
            )


class EnvIO:
    """Handle environment read/write."""

    def __init__(self, env_directory: Optional[PathLike] = None):
        self.env_dir = Path(env_directory)
        self._setup_env_dir()

    def _setup_env_dir(self) -> None:
        """set up the env directory"""
        if not self.env_dir.is_dir():
            self.env_dir.mkdir(parents=True)

    def delete_all(self) -> None:
        """Delete all files in the environment directory."""
        shutil.rmtree(self.env_dir)

    def export_install_r(self, contents: str) -> None:
        """export the install.R file"""
        file = self.env_dir / "install.R"
        file.write_text(contents)

    def delete_install_r(self) -> None:
        """delete the install.R file"""
        file = self.env_dir / "install.R"
        if file.is_file():
            file.unlink()

    def export_packages(self, contents: str) -> None:
        """export just packages with versions"""
        file = self.env_dir / "conda-env.yaml"
        formatted = self._format_yaml(contents)
        file.write_text(formatted)

    def copy_environment(self, path: PathLike) -> None:
        """Copy the environment files.
        """
        path = Path(path)
        for file_name in ["conda-env.yaml", "history.yaml", "install.R"]:
            file = self.env_dir / file_name
            if file.exists():
                shutil.copy(file, path / file_name)

    def get_environment(self) -> Optional[dict]:
        """Get the environment file as a dict."""
        file = self.env_dir / "conda-env.yaml"
        if file.exists():
            local_env = file.read_text()
            return yaml.load(local_env, Loader=yaml.FullLoader)
        return None

    def get_history(self) -> Optional[History]:
        """return history from history.yaml"""
        log_file = self.env_dir / "history.yaml"
        if log_file.is_file():
            log_content = log_file.read_text()
            return History.parse(yaml.load(log_content, Loader=yaml.FullLoader))
        return None

    def write_history_file(self, history: History) -> None:
        """write/update history yaml file"""
        self._setup_env_dir()
        log_file = self.env_dir / "history.yaml"
        contents = yaml.dump(history.export(), default_flow_style=False)
        formatted = self._format_yaml(contents)
        log_file.write_text(formatted)

    def set_remote_dir(
        self, remote_dir: PathLike, if_missing: bool = False, yes: bool = False
    ) -> None:
        """Create remote file and write setup directory.

        If the remote file already exists, then prompt the user before changing the remote directory.
        """
        remote_dir = Path(remote_dir).absolute()
        remote_file = self.env_dir / "remote.txt"
        if (
            not yes
            and remote_file.exists()
            and if_missing
            and remote_file.read_text() != str(remote_dir)
        ):
            sys.exit(
                f"Current remote directory {remote_file.read_text()} for cet at {self.env_dir} is not same as new remote {remote_dir}"
            )
        if (
            yes
            or not remote_file.exists()
            or (
                remote_file.read_text() != str(remote_dir)
                and conda_env_tracker.utils.prompt_yes_no(
                    f'Overwrite cet current remote directory "{remote_file.read_text()}"'
                    f' with "{remote_dir}"'
                )
            )
        ):
            remote_file.write_text(str(remote_dir))

    def get_remote_dir(self) -> str:
        """Get remote setup file"""
        remote_file = self.env_dir / "remote.txt"
        if not remote_file.is_file():
            raise CondaEnvTrackerRemoteError(
                'Conda-env-tracker remote is not configured. Please use "cet remote --help"'
            )
        return remote_file.read_text()

    def is_remote_dir_set(self) -> bool:
        """Return True if the remote setup file exists, False otherwise."""
        return (self.env_dir / "remote.txt").is_file()

    @staticmethod
    def overwrite_local(local_io, remote_io) -> None:
        """overwrite local directory with remote directory. The try statement is meant to
        keep files that are not stored in the git repo when updated local environment files.
        For example, 'remote.txt' will be in the local '.cet' directory but should not
        be in the git repo because it contains a user specific path."""
        temp_dir = local_io.env_dir.parent / ("." + str(local_io.env_dir.name))
        local_io.env_dir.rename(target=temp_dir)
        try:
            shutil.copytree(remote_io.env_dir, local_io.env_dir)
            extra_files = set(file.name for file in temp_dir.iterdir()) - set(
                file.name for file in local_io.env_dir.iterdir()
            )
            for file in extra_files:
                (temp_dir / file).replace(local_io.env_dir / file)
        except Exception:  # pylint: disable=broad-except
            temp_dir.rename(target=local_io.env_dir.name)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _format_yaml(contents: str) -> str:
        """Ensure that there are two spaces per level in yaml file."""
        if "\n- " in contents:
            lines = contents.split("\n")
            previous_line_indented = False
            for index, line in enumerate(lines):
                if line and (
                    line.lstrip().startswith("-")
                    or (line.startswith(" ") and previous_line_indented)
                ):
                    lines[index] = "  " + line
                    previous_line_indented = True
                else:
                    previous_line_indented = False
            return "\n".join(lines)
        return contents
