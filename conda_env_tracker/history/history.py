"""The classes to represent the history of the environment for reproducibility and transparency."""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from conda_env_tracker.channels import Channels
from conda_env_tracker.gateways.conda import get_dependencies
from conda_env_tracker.packages import Package, Packages

from conda_env_tracker.errors import CondaEnvTrackerParseHistoryError
from conda_env_tracker.history.actions import Actions
from conda_env_tracker.history.debug import Debug
from conda_env_tracker.history.diff import Diff
from conda_env_tracker.history.logs import Logs
from conda_env_tracker.history.packages import PackageRevision
from conda_env_tracker.history.revisions import Revisions
from conda_env_tracker.types import ListLike


logger = logging.getLogger(__name__)


class History:
    """The history of the habitat environment."""

    history_file_version = "1.0"

    def __init__(
        self,
        name: str,
        id: str,
        channels: Channels,
        packages: PackageRevision,
        revisions: Revisions,
    ):
        self.name = name
        self.id = id
        self.channels = channels
        self.packages = packages
        self.revisions = revisions
        self.diff = None
        self.logs = self.revisions.logs
        self.actions = self.revisions.actions
        self.debug = self.revisions.debug

    @classmethod
    def create(
        cls,
        name: str,
        channels: Channels,
        packages: PackageRevision,
        logs: Logs,
        actions: Actions,
        diff: Diff,
        debug: Debug,
    ):
        """Create the history for a new habitat environment."""
        id = str(uuid4())
        revisions = Revisions.create(
            logs=logs, actions=actions, packages=packages, diff=diff, debug=debug
        )
        return cls(
            name=name, id=id, channels=channels, packages=packages, revisions=revisions
        )

    def append(self, log: str, action: str):
        """Append to the environment history."""
        self.revisions.append_revision(
            log=log,
            action=action,
            packages=self.packages,
            diff=self.diff,
            name=self.name,
        )

    def update_packages(
        self, dependencies: dict, packages: Optional[Packages] = None, source="conda"
    ):
        """Update the packages for the current revision of the environment."""
        self.diff = Diff.compute(
            packages=self.packages,
            dependencies=dependencies,
            upsert_packages=packages,
            source=source,
        )
        if packages:
            self.packages.update_packages(packages=packages, source=source)
        self.packages.update_versions(dependencies=dependencies)

    def remove_packages(self, packages: Packages, dependencies: dict, source="conda"):
        """Remove packages from the current revision of the environment."""
        self.diff = Diff.compute(
            packages=self.packages, dependencies=dependencies, source=source
        )
        self.packages.remove_packages(packages=packages, source=source)
        self.packages.update_versions(dependencies=dependencies)

    @classmethod
    def parse(cls, history_content: dict):
        """Parse the history from the file."""
        try:
            sections = {
                "name": history_content.get("name"),
                "id": history_content.get("id"),
                "channels": Channels(history_content.get("channels")),
                "revisions": Revisions.parse(history_content.get("revisions")),
                "packages": PackageRevision.parse(history_content.get("packages")),
            }
            return cls(**sections)
        except Exception as err:
            raise CondaEnvTrackerParseHistoryError(
                f"Failed to parse history with error: {err}"
            )

    def export(self) -> Dict[str, Any]:
        """export the packages as yaml/json string"""
        return {
            "name": self.name,
            "id": self.id,
            "history-file-version": self.history_file_version,
            "channels": [channel for channel in self.channels],
            "packages": self.packages.export(),
            "revisions": self.revisions.export(),
        }

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

    def __repr__(self) -> str:
        return (
            f"History(name={self.name}, channels={self.channels}, packages={self.packages}, "
            f"revisions={self.revisions})"
        )

    def __eq__(self, other) -> bool:
        """Check that they are the same type and that their attributes are equal."""
        attributes = ["name", "id", "channels", "revisions", "packages"]
        if not isinstance(other, type(self)):
            return False
        for attribute in attributes:
            if getattr(self, attribute) != getattr(other, attribute):
                return False
        return True
