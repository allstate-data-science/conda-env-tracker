"""Installing, updating and removing conda packages."""
from typing import Callable

from conda_env_tracker.channels import Channels
from conda_env_tracker.gateways.conda import (
    conda_install,
    conda_remove,
    conda_update_all,
    get_conda_install_command,
    get_conda_remove_command,
    get_conda_update_all_command,
)
from conda_env_tracker.env import Environment
from conda_env_tracker.packages import Packages
from conda_env_tracker.types import ListLike


class CondaHandler:
    """Handle interaction with conda packages."""

    def __init__(self, env: Environment):
        self.env = env

    def install(
        self,
        packages: Packages,
        channels: ListLike = None,
        yes: bool = False,
        strict_channel_priority: bool = True,
    ) -> None:
        """Install/update conda packages"""
        conda_install(
            name=self.env.name,
            packages=packages,
            channel_command=self.env.history.channels.create_channel_command(
                preferred_channels=channels,
                strict_channel_priority=strict_channel_priority,
            ),
            yes=yes,
        )
        self.update_history_install(
            packages=packages,
            channels=channels,
            strict_channel_priority=strict_channel_priority,
        )
        self.env.export()

    def remove(
        self, packages: Packages, channels: ListLike = None, yes: bool = False
    ) -> None:
        """Remove conda packages"""
        channel_command = self._get_conda_remove_channel_command(channels=channels)
        conda_remove(
            name=self.env.name,
            packages=packages,
            channel_command=channel_command,
            yes=yes,
        )
        self.update_history_remove(packages=packages, channels=channels)
        self.env.export()

    def update_all(
        self,
        packages: Packages = (),
        channels: ListLike = None,
        yes: bool = False,
        strict_channel_priority: bool = True,
    ) -> None:
        """Update all conda packages"""
        conda_update_all(
            name=self.env.name,
            packages=packages,
            channels=self.env.history.channels.create_channel_command(
                preferred_channels=channels,
                strict_channel_priority=strict_channel_priority,
            ),
            yes=yes,
        )
        self.update_history_update_all(
            packages=packages,
            channels=channels,
            strict_channel_priority=strict_channel_priority,
        )
        self.env.export()

    def update_history_install(
        self,
        packages: Packages,
        channels: ListLike = None,
        strict_channel_priority: bool = True,
    ):
        """Update the history file for conda installs."""
        self._update_history(
            get_command=get_conda_install_command,
            packages=packages,
            channels=channels,
            strict_channel_priority=strict_channel_priority,
        )

    def update_history_update_all(
        self,
        packages: Packages = (),
        channels: ListLike = None,
        strict_channel_priority: bool = True,
    ):
        """Update the history file for conda update --all.

        The conda packages in the history file cannot have a custom spec after update --all.
        """
        self._update_history(
            get_command=get_conda_update_all_command,
            packages=packages,
            channels=channels,
            strict_channel_priority=strict_channel_priority,
        )
        package_names = {pkg.name for pkg in packages}
        for package in self.env.history.packages["conda"].values():
            if package.name != "python" and package.name not in package_names:
                package.spec = package.name

    def _update_history(
        self,
        get_command: Callable,
        packages: Packages,
        channels: ListLike,
        strict_channel_priority: bool = True,
    ):
        self.env.update_dependencies()
        self.env.history.update_packages(
            packages=packages, dependencies=self.env.dependencies
        )

        self.env.validate_packages(packages)

        log = get_command(name=self.env.name, packages=packages)
        if channels:
            log = log + " " + Channels.format_channels(channels)

        specs = self.env.history.actions.get_package_specs(
            packages=packages, dependencies=self.env.dependencies["conda"]
        )

        channel_string = self.env.history.channels.create_channel_command(
            preferred_channels=channels, strict_channel_priority=strict_channel_priority
        )
        command_with_specs = get_command(
            name=self.env.name, packages=Packages.from_specs(specs)
        )
        action = f"{command_with_specs} {channel_string}"

        self.env.history.append(log=log, action=action)

    def update_history_remove(
        self, packages: Packages, channels: ListLike = None
    ) -> None:
        """Update history for conda remove."""
        self.env.update_dependencies()
        self.env.history.remove_packages(
            packages=packages, dependencies=self.env.dependencies
        )
        self.env.validate_packages()

        remove_command = get_conda_remove_command(name=self.env.name, packages=packages)
        if channels:
            log = remove_command + " " + Channels.format_channels(channels)
        else:
            log = remove_command

        channel_command = self._get_conda_remove_channel_command(channels=channels)
        action = f"{remove_command} {channel_command}"

        self.env.history.append(log=log, action=action)

    def _get_conda_remove_channel_command(self, channels: ListLike = None):
        """The conda remove command does not support strict channel priority."""
        channel_command = self.env.history.channels.create_channel_command(
            preferred_channels=channels, strict_channel_priority=False
        )
        return channel_command
