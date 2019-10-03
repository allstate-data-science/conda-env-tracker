"""The list of revisions in the history."""
import copy
from typing import List

from conda_env_tracker.history.actions import Actions
from conda_env_tracker.history.debug import Debug
from conda_env_tracker.history.diff import Diff
from conda_env_tracker.history.logs import Logs
from conda_env_tracker.history.packages import PackageRevision


class Revisions:
    """The list of every revision to the environment (i.e. adding packages, removing packages or updating packages)."""

    def __init__(
        self,
        logs: Logs,
        actions: Actions,
        packages: List[PackageRevision],
        diffs: List[Diff],
        debug: Debug,
    ):
        self.logs = logs
        self.actions = actions
        self.packages = packages
        self.diffs = diffs
        self.debug = debug

    @classmethod
    def create(
        cls,
        logs: Logs,
        actions: Actions,
        packages: PackageRevision,
        diff: Diff,
        debug: Debug,
    ):
        """Create a new set of revisions for a new environment."""
        return cls(
            logs=logs,
            actions=actions,
            packages=[copy.deepcopy(packages)],
            diffs=[diff],
            debug=debug,
        )

    def append_revision(
        self, log: str, action: str, packages: PackageRevision, diff: Diff, name: str
    ):
        """Add the command details to the history of environment revisions."""
        self.logs.append(log)
        self.actions.append(action)
        self.packages.append(copy.deepcopy(packages))
        self.diffs.append(diff)
        self.debug.update(name=name)

    def export(self):
        """Export to dump into a file and make sure not to mutate state."""
        exported = []
        for log, action, packages, diff, debug in zip(
            self.logs, self.actions, self.packages, self.diffs, self.debug
        ):
            row = {}
            row["packages"] = packages.export()
            row["diff"] = diff.export()
            row["log"] = log
            row["action"] = action
            row["debug"] = debug
            exported.append(row)
        return exported

    @classmethod
    def parse(cls, history_section: list):
        """Parse the revision section of the history file."""
        logs = Logs()
        actions = Actions()
        packages = []
        diffs = []
        debug = Debug()
        for revision in history_section:
            logs.append(revision["log"])
            actions.append(revision["action"])
            packages.append(PackageRevision.parse(revision["packages"]))
            diffs.append(Diff.parse(revision["diff"]))
            debug.append(revision["debug"])
        return cls(
            logs=logs, actions=actions, packages=packages, diffs=diffs, debug=debug
        )

    def __repr__(self) -> str:
        return f"Revisions(logs={self.logs}, actions={self.actions}, packages={self.packages}, debug={self.debug})"

    def __eq__(self, other):
        if (
            isinstance(other, Revisions)
            and self.logs == other.logs
            and self.actions == other.actions
            and self.packages == other.packages
            and self.debug == other.debug
        ):
            return True
        return False
