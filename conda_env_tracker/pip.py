"""Installing, updating and removing pip packages."""
from typing import Union

from conda_env_tracker.gateways.pip import (
    get_pip_install_command,
    get_pip_custom_install_command,
    pip_install,
    pip_remove,
    get_pip_remove_command,
    pip_custom_install,
    PIP_DEFAULT_INDEX_URL,
)
from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.types import ListLike


class PipHandler:
    """Handle interactions with pip packages."""

    def __init__(self, env: "Environment"):
        self.env = env

    def install(
        self,
        packages: Packages,
        index_url: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL,
    ) -> None:
        """Install/update pip packages"""
        pip_install(name=self.env.name, packages=packages, index_url=index_url)
        self.update_history_install(packages=packages, index_url=index_url)
        self.env.export()

    def custom_install(self, package: Package) -> None:
        """Install with custom urls"""
        pip_custom_install(name=self.env.name, package=package)
        self.update_history_custom_urls(package=package)
        self.env.export()

    def update_history_install(
        self,
        packages: Packages,
        index_url: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL,
    ):
        """Update history for pip install."""
        self.env.update_dependencies()
        self.env.history.update_packages(
            packages=packages, dependencies=self.env.dependencies, source="pip"
        )
        self.env.validate_packages(packages, source="pip")

        log = get_pip_install_command(packages=packages, index=index_url)

        specs = self.env.history.actions.get_package_specs(
            packages=packages,
            dependencies=self.env.dependencies["pip"],
            version_separator="==",
        )
        action = get_pip_install_command(
            packages=Packages.from_specs(specs), index=index_url
        )

        self.env.history.append(log=log, action=action)

    def update_history_custom_urls(self, package: Package):
        """Update history for pip install with custom urls"""
        self.env.update_dependencies()
        self.env.history.update_packages(
            packages=Packages(package), dependencies=self.env.dependencies, source="pip"
        )
        self.env.validate_packages(Packages(package), source="pip")
        log = get_pip_custom_install_command(spec=package.spec)
        self.env.history.append(log=log, action=log)

    def remove(self, packages: Packages, yes: bool = False):
        """Remove the pip package including custom pip package"""
        pip_remove(name=self.env.name, packages=packages, yes=yes)
        self.env.update_dependencies()
        self.update_history_remove(packages=packages)
        self.env.export()

    def update_history_remove(self, packages: Packages) -> None:
        """Update history for pip remove."""
        self.env.history.remove_packages(
            packages=packages, dependencies=self.env.dependencies, source="pip"
        )
        self.env.validate_packages(source="pip")
        remove_command = get_pip_remove_command(packages=packages, yes=False)
        self.env.history.append(log=remove_command, action=remove_command)
