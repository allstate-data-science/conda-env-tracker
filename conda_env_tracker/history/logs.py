"""The log of the user command."""
import re
from typing import Union, Optional

from conda_env_tracker.errors import CondaEnvTrackerParseHistoryError
from conda_env_tracker.gateways.r import R_COMMAND
from conda_env_tracker.packages import Packages, Package
from conda_env_tracker.types import ListLike


class Logs(list):
    """The log of the user creation and install commands for the environment."""

    def __init__(self, logs: Optional[Union[str, ListLike]] = None):
        if isinstance(logs, str):
            logs = [logs]
        if logs:
            list.__init__(self, logs)
        else:
            list.__init__(self)

    def extract_packages(self, index: int, packages: Packages) -> Packages:
        """Return the packages for the log item"""
        if self._is_r_log(index):
            return self.extract_r_packages(index)
        return self._extract_packages(index, packages)

    def _extract_packages(self, index: int, packages: Packages) -> Packages:
        """Extracting conda and pip packages"""
        log = self[index]
        extracted_packages = Packages()
        for package in packages:
            package_expression = re.compile(f"(({package.name})(=[a-z0-9_=.]+)?)")
            spec = package_expression.search(log).group(0)
            extracted_packages.append_spec(spec)
        return extracted_packages

    def extract_r_packages(self, index: int) -> Optional[Packages]:
        """Extract R packages with versions (if the version was specified in the log)."""
        if self[index].startswith(R_COMMAND):
            r_packages = Packages()
            quote = '"'
            package_names = self._get_r_package_names(self[index])
            start = self[index].index(quote) + len(quote)
            r_commands = self[index]
            for package_name in package_names:
                i_name = r_commands.index(package_name)
                try:
                    end = r_commands.index(";", i_name)
                except ValueError:
                    end = r_commands.rindex(quote, i_name)
                spec = r_commands[start:end].strip()
                start = end + 1
                r_packages.append(Package(package_name, spec.replace(r"\"", '"')))
            return r_packages
        return None

    @staticmethod
    def _get_r_package_names(log: str) -> ListLike:
        package_names = []
        splits = log.split(r"install_mran(\"")
        for split in splits[1:]:
            end = split.index(r"\"")
            package_names.append(split[:end])
        return package_names

    def _is_r_log(self, index) -> bool:
        return self[index].startswith(R_COMMAND)

    def extra_removed_packages(self, index: int) -> Packages:
        """Extract packages from a remove command.

        The package names always occur after the --name, but we have to drop the environment name
        """
        log = self[index]
        if (
            not log.startswith("conda remove")
            and not log.startswith("pip uninstall")
            and not (log.startswith(R_COMMAND) and "remove.packages" in log)
        ):
            raise CondaEnvTrackerParseHistoryError(
                f"The log at index {index} is not a remove statement: {self[index]}."
            )
        if log.startswith("conda remove"):
            package_names = self._extract_conda_remove_package_names(log)
        elif log.startswith("pip uninstall"):
            package_names = log.replace("pip uninstall ", "").split()
        else:
            package_names = self._extract_r_remove_package_names(log)
        return Packages.from_specs(package_names)

    @staticmethod
    def _extract_conda_remove_package_names(log):
        """All package names occur after --name and we need to drop the environment name."""
        names = log.split("--name")[-1].split()
        return names[1:]

    @staticmethod
    def _extract_r_remove_package_names(log):
        """Parsing removed R packages which occur inside a vector passed to remove.packages."""
        start = "remove.packages(c("
        i_start = log.find(start) + len(start)
        i_end = log.find(")", i_start)
        package_names = [name.strip(r"\"") for name in log[i_start:i_end].split(",")]
        return package_names

    def extract_channels(self, index: int) -> ListLike:
        """Get the list of channels (if any) from a conda install command in the logs."""
        cmd_pieces = self[index].split()
        channels = []
        for i, piece in enumerate(cmd_pieces):
            if piece in ["--channel", "-c"]:
                channels.append(cmd_pieces[i + 1])
        return channels

    def extract_index_urls(self, index: int) -> ListLike:
        """Get the list of index urls from a pip install command in the logs."""
        cmd_pieces = self[index].split()
        index_urls = []
        for i, piece in enumerate(cmd_pieces):
            if piece in ["--index-url", "--extra-index-url"]:
                index_urls.append(cmd_pieces[i + 1])
        return index_urls
