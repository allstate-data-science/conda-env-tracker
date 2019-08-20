"""The classes to represent the history of the environment for reproducibility and transparency."""

import logging
import re
import datetime
from typing import Any, Dict, Optional

from conda_env_tracker.channels import Channels
from conda_env_tracker.gateways.conda import get_dependencies, CONDA_VERSION
from conda_env_tracker.errors import (
    CondaEnvTrackerChannelError,
    CondaEnvTrackerError,
    CondaEnvTrackerParseHistoryError,
)
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.gateways.pip import get_pip_version
from conda_env_tracker.gateways.r import R_COMMAND
from conda_env_tracker.types import ListLike
from conda_env_tracker.gateways.utils import get_platform_name

logger = logging.getLogger(__name__)


class Logs(list):
    """The log of the user creation and install commands for the environment."""

    @classmethod
    def create(cls, command: str):
        """Wrap the initial create command in a list."""
        logs = cls()
        logs.append(command)
        return logs

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
            install_commands = self[index].split(";")[1:]
            for command in install_commands:
                start = command.index('"') + 1
                end = command.index('"', start)
                name = command[start:end]
                if "version" in command:
                    start = command.index('"', end + 1) + 1
                    end = command.index('"', start)
                    version = command[start:end]
                    r_packages.append_spec(f"{name}={version}")
                else:
                    r_packages.append_spec(name)
            return r_packages
        return None

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
        package_names = [name.strip('"') for name in log[i_start:i_end].split(",")]
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


class Actions(list):
    """The actions with complete package versions and build strings that will reproduce the current environment."""

    @classmethod
    def create(
        cls,
        name: str,
        specs: ListLike,
        channels: Channels,
        yes: bool = False,
        strict_channel_priority: bool = True,
    ):
        """return the action string"""
        if not channels:
            raise CondaEnvTrackerChannelError("Could not find user channels.")
        channel_string = channels.create_channel_command(
            strict_channel_priority=strict_channel_priority
        )
        actions = cls()
        if yes:
            prefix_cmd = f"conda create -y --name {name} "
        else:
            prefix_cmd = f"conda create --name {name} "
        actions.append(prefix_cmd + " ".join(specs) + " " + channel_string)
        return actions

    def extract_packages(self, index: int) -> Packages:
        """Return the packages for the action item"""
        if self._is_r_action(index):
            packages, _ = self.extract_r_packages(index)
            return packages
        package_expression = re.compile("([a-z0-9-_.]+=[a-z0-9_=.]+)")
        return Packages.from_specs(
            [spec for spec in package_expression.findall(self[index])]
        )

    def extract_r_packages(self, index: int) -> (Packages, list):
        """Get the package and date from an R action."""
        action = self[index]
        packages = Packages()
        dates = []
        install_commands = action.split(";")[1:]
        for command in install_commands:
            start = command.index('"') + 1
            end = command.index('"', start)
            name = command[start:end]
            start = command.index('"', end + 1) + 1
            end = command.index('"', start)
            version = command[start:end]
            packages.append_spec(f"{name}={version}")
            start = command.index('"', end + 1) + 1
            end = command.index('"', start)
            date = command[start:end]
            dates.append(date)
        return packages, dates

    def _is_r_action(self, index) -> bool:
        return self[index].startswith(R_COMMAND)

    @staticmethod
    def get_package_specs(
        packages: Packages, dependencies: dict, version_separator="="
    ) -> ListLike:
        """Return the package spec with version."""
        specs = []
        for package in packages:
            if package.name not in dependencies:
                raise CondaEnvTrackerError(
                    f"package [{package.name}] does not exist in conda environment"
                )
            package.version = dependencies[package.name].version
            package.build = dependencies[package.name].build
            specs.append(package.create_spec(separator=version_separator))
        return specs


class HistoryPackages(dict):
    """Importing and exporting user specified package infromation in the history."""

    sources = ["conda", "pip"]
    separators = {"conda": "=", "pip": "==", "r": "="}

    def update_packages(self, packages: Packages, source="conda") -> None:
        """Update the conda packages."""
        self[source] = self.get(source, {})
        self._update_packages(self[source], packages)

    @staticmethod
    def _update_packages(existing: dict, new: Packages) -> None:
        for package in new:
            existing[package.name] = package

    def remove_packages(self, packages: Packages, source="conda") -> None:
        """Remove packages."""
        for package in packages:
            self[source].pop(package.name, None)

    @classmethod
    def create(cls, packages: Packages):
        """Create an instance of the HistoryPackages class from a list of packages."""
        packages_instance = cls()
        packages_instance.update_packages(packages=packages)
        return packages_instance

    @classmethod
    def parse(cls, history_section: dict):
        """Parse the history file and create the packages."""
        packages_instance = cls()
        for source, packages in history_section.items():
            source_packages = Packages()
            for name, spec in packages.items():
                if spec == "*":
                    source_packages.append_spec(name)
                elif spec[0].isdigit() and all(
                    letter.isalnum() or letter in [".", "=", "_"] for letter in spec
                ):
                    source_packages.append_spec(name + cls.separators[source] + spec)
                else:
                    source_packages.append(Package(name, spec))
            packages_instance.update_packages(packages=source_packages, source=source)
        return packages_instance

    def export(self) -> dict:
        """Export the packages with '*' for version if none was specified."""
        output = {}
        for source, packages in self.items():
            source_packages = {}
            for name, info in packages.items():
                if info.spec_is_custom():
                    source_packages[name] = info.spec
                else:
                    version = info.get_version_from_spec()
                    if version:
                        source_packages[name] = version
                    else:
                        source_packages[name] = "*"
            if source_packages:
                output[source] = source_packages
        return output


class Debug(list):
    """Debug information about each step in the history of the file."""

    def __init__(self, debug=None):
        list.__init__(self)
        if debug:
            self.extend(debug)

    @classmethod
    def create(cls, name: str):
        """Create the class with the first set of debug information."""
        debug = cls()
        debug.update(get_pip_version(name=name))
        return debug

    def update(self, pip_version=None) -> None:
        """Update with the current debug information."""
        self.append(
            {
                "platform": get_platform_name(),
                "conda_version": CONDA_VERSION,
                "pip_version": pip_version,
                "timestamp": str(datetime.datetime.now()),
            }
        )


class History:
    """The history of the cet environment."""

    classes = {
        "name": str,
        "channels": Channels,
        "packages": HistoryPackages,
        "logs": Logs,
        "actions": Actions,
        "debug": Debug,
    }

    def __init__(
        self,
        name: str,
        channels: Channels,
        packages: HistoryPackages,
        logs: Logs,
        actions: Actions,
        debug: Debug,
    ):
        self.name = name
        self.channels = channels
        self.packages = packages
        self.logs = logs
        self.actions = actions
        self.debug = debug

    def __repr__(self) -> str:
        return (
            f"History(name={self.name}, channels={self.channels}, packages={self.packages}, "
            f"logs={self.logs}, actions={self.actions}, debug={self.debug})"
        )

    def __eq__(self, other) -> bool:
        """Check that they are the same type and that their attributes are equal."""
        if not isinstance(other, type(self)):
            return False
        for attribute in self.classes:
            if getattr(self, attribute) != getattr(other, attribute):
                return False
        return True

    def append(self, log: str, action: str):
        """Append to the environment history."""
        self.logs.append(log)
        self.actions.append(action)
        self.debug.update(pip_version=get_pip_version(name=self.name))

    @classmethod
    def parse(cls, history_content: dict):
        """parse the history from log file"""
        sections = cls._parse_sections(history_content)
        return cls(**sections)

    @classmethod
    def _parse_sections(cls, content: dict) -> Dict[str, Any]:
        """Parse each section of the history file."""
        sections = {}
        for name, section_cls in cls.classes.items():
            section = content.get(name)
            if section:
                try:
                    sections[name] = section_cls.parse(section)
                except AttributeError:
                    sections[name] = section_cls(section)
            else:
                sections[name] = section_cls()
        return sections

    def export(self) -> Dict[str, Any]:
        """export the packages as yaml/json string"""
        return {
            "name": self.name,
            "channels": [channel for channel in self.channels],
            "packages": self.packages.export(),
            "logs": [log for log in self.logs],
            "actions": [action for action in self.actions],
            "debug": [debug for debug in self.debug],
        }

    def get_packages_with_implicit_version_change(
        self, dependencies: dict, source: str
    ) -> ListLike:
        """Returns the list of packages with user specified versions that were updated implicitly."""
        modified_packages = []
        source_packages = self.packages[source]
        for name, package in source_packages.items():
            if not package.spec == name:
                dep = dependencies[source][name]
                version = package.get_version_from_spec(ignore_build=True)
                if version and not dep.version.startswith(version):
                    dep.spec = dep.create_spec()
                    source_packages[name] = dep
                    modified_packages.append(dep)

        return modified_packages

    @staticmethod
    def history_diff(env_name: str, env, env_reader) -> ListLike:
        """return the difference between history and local environment"""
        version_diff_pkges: ListLike = []
        new_pkges: ListLike = []
        missing_pkges: ListLike = []

        history_conda_pkges = env_reader.get_environment()["dependencies"]
        history_conda_pkges_dict = {}
        for spec in history_conda_pkges:
            name, package = Package.from_spec(spec)
            history_conda_pkges_dict[name] = package
        local_conda_pkges = get_dependencies(name=env_name)["conda"]
        for name, package in local_conda_pkges.items():
            if name in history_conda_pkges_dict:
                if package.version != history_conda_pkges_dict[name].version:
                    version_diff_pkges.append(
                        "-" + name + "=" + history_conda_pkges_dict[name]
                    )
                    version_diff_pkges.append("+" + name + "=" + package.version)
            else:
                new_pkges.append("+" + name + "=" + package.version)
        for package in env.history.packages["conda"]:
            if package not in local_conda_pkges.keys():
                missing_pkges.append("-" + package)

        return version_diff_pkges, new_pkges, missing_pkges
