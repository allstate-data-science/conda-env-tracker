"""The full action taken by conda_env_tracker to update the user environment."""
import re

from conda_env_tracker.channels import Channels
from conda_env_tracker.errors import CondaEnvTrackerChannelError, CondaEnvTrackerError
from conda_env_tracker.gateways.r import R_COMMAND
from conda_env_tracker.packages import Packages
from conda_env_tracker.types import ListLike


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
            raise CondaEnvTrackerChannelError("Could not find the channels")
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
        package_expression = re.compile("([a-z0-9-_.]+=[a-z0-9_=.]+)")
        return Packages.from_specs(
            [spec for spec in package_expression.findall(self[index])]
        )

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
