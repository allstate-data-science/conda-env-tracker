"""Pull environment from remote to local."""
# pylint: disable=too-many-return-statements
import logging
from typing import Optional

from conda_env_tracker.conda import CondaHandler
from conda_env_tracker.env import Environment
from conda_env_tracker.errors import (
    CondaEnvTrackerCreationError,
    CondaEnvTrackerRemoteError,
    CondaEnvTrackerPullError,
)
from conda_env_tracker.gateways.conda import update_conda_environment
from conda_env_tracker.gateways.io import EnvIO
from conda_env_tracker.gateways.r import update_r_environment, R_COMMAND
from conda_env_tracker.history import History
from conda_env_tracker.packages import Packages
from conda_env_tracker.pip import PipHandler
from conda_env_tracker.r import RHandler
from conda_env_tracker.types import PathLike
from conda_env_tracker.utils import prompt_yes_no, is_ordered_subset

logger = logging.getLogger(__name__)


def pull(env: Environment, yes: bool = False) -> Environment:
    """Pull history from remote to local"""
    try:
        remote_dir = env.local_io.get_remote_dir()
    except CondaEnvTrackerRemoteError as remote_err:
        raise CondaEnvTrackerPullError(str(remote_err))
    remote_io = EnvIO(env_directory=remote_dir)
    remote_history = remote_io.get_history()

    local_history = env.history

    if _create_env_with_new_id(env=env, remote_history=remote_history, yes=yes):
        return replace_local_with_remote(
            env=env,
            remote_dir=remote_dir,
            remote_io=remote_io,
            remote_history=remote_history,
        )
    if _nothing_to_pull(local_history=local_history, remote_history=remote_history):
        logger.info("Nothing to pull.")
        return env
    if _local_needs_update(
        local_history=local_history, remote_history=remote_history, yes=yes
    ):
        return replace_local_with_remote(
            env=env,
            remote_dir=remote_dir,
            remote_io=remote_io,
            remote_history=remote_history,
        )

    if not yes and not prompt_yes_no(
        prompt_msg=(
            "Remote and local have different packages, do you want to overwrite "
            "with remote and append local"
        )
    ):
        logger.info("Exiting without updating local environment.")
        raise CondaEnvTrackerPullError(
            "Conflicting Packages in remote and local; user elected not to update"
        )

    return merge_conflicting_changes(env=env)


def merge_conflicting_changes(env: Environment):
    """Reconciles packages between local and remote"""
    remote_dir = env.local_io.get_remote_dir()
    remote_io = EnvIO(env_directory=remote_dir)
    remote_history = remote_io.get_history()

    local_history = env.history
    update_conda_environment(env_dir=remote_dir)
    if _r_env_needs_updating(
        local_history=local_history, remote_history=remote_history
    ):
        update_r_environment(name=env.name, env_dir=remote_dir)
    EnvIO.overwrite_local(local_io=env.local_io, remote_io=remote_io)
    new_env = Environment(name=env.name, history=remote_history)
    new_env.validate()
    extra_logs = []
    for log in local_history.logs:
        if log not in set(remote_history.logs):
            extra_logs.append(log)
    for log in extra_logs:
        new_env = _update_from_extra_log(env=new_env, history=local_history, log=log)

    new_env.validate()
    new_env.export()

    env.history = new_env.history
    logger.info("Successfully updated the environment.")
    return new_env


def replace_local_with_remote(
    env: Environment, remote_dir: PathLike, remote_io: EnvIO, remote_history: History
):
    """Update the environment and history."""
    update_conda_environment(env_dir=remote_dir)
    if _r_env_needs_updating(env.history, remote_history):
        update_r_environment(name=env.name, env_dir=remote_dir)
    EnvIO.overwrite_local(local_io=env.local_io, remote_io=remote_io)
    env.replace_history(history=remote_history)
    env.validate()
    logger.info("Successfully updated the environment.")
    return env


def _nothing_to_pull(local_history: History, remote_history: History) -> bool:
    """Either there is no remote history or the local is up-to-date with remote."""
    if not remote_history:
        return True
    if local_history and _no_new_actions_in_remote(
        local_history=local_history, remote_history=remote_history
    ):
        return True
    return False


def _create_env_with_new_id(env: Environment, remote_history: History, yes: bool):
    if env.history and remote_history and env.history.id != remote_history.id:
        if yes or prompt_yes_no(
            prompt_msg=(
                f"The remote cet environment ({env.local_io.get_remote_dir()}) doesn't match the local environment ({env.name})\n"
                "Would you like to replace your local environment"
            ),
            default=False,
        ):
            return True
        raise CondaEnvTrackerCreationError(
            f"The remote environment ({env.local_io.get_remote_dir()}) appears to be new environment and would replace the current local environment ({env.name})\n"
            "User elected not to update"
        )
    return False


def _local_needs_update(
    local_history: History, remote_history: History, yes: bool = True
) -> bool:
    """Either the local does not yet exist or local is a subset of remote."""
    if not local_history and remote_history:
        return True
    if _no_new_actions_in_local(
        local_history=local_history, remote_history=remote_history
    ):
        return True
    if _actions_in_different_order(
        local_history=local_history, remote_history=remote_history
    ):
        if not yes and not prompt_yes_no(
            prompt_msg="Remote environment has same packages but in different order, "
            "Should we overwrite local with remote environment"
        ):
            raise CondaEnvTrackerPullError(
                "Actions in a different order; user elected not to update"
            )
        return True
    return False


def _r_env_needs_updating(local_history: History, remote_history: History) -> bool:
    """If there is an R command in remote that is not in local, then we return True."""
    if not local_history:
        new_actions = remote_history.actions
    else:
        new_actions = set(remote_history.actions) - set(local_history.actions)
    for action in new_actions:
        if action.startswith(R_COMMAND):
            return True
    return False


def _update_from_extra_log(env: Environment, history: History, log: str) -> Environment:
    """Update the local history and environment from the extra log entry."""
    index = history.logs.index(log)
    if log.startswith("conda"):
        env = _handle_conda_extra_log(env=env, history=history, index=index)
    elif log.startswith("pip"):
        env = _handle_pip_extra_log(env=env, history=history, index=index)
    elif log.startswith(R_COMMAND):
        _handle_r_extra_log(env=env, history=history, index=index)

    env = _update_history_packages_spec_from_log(env, history, log)
    return env


def _update_history_packages_spec_from_log(
    env: Environment, history: History, log: str
):
    """Since we ran the action with specific versions the packages in the history will have the wrong spec.
    We extract the spec from the log in the history and then update the packages.
    """
    index = history.logs.index(log)
    if (
        log.startswith("conda remove")
        or log.startswith("pip uninstall")
        or log.startswith(R_COMMAND)
    ):
        return env
    action_packages = history.actions.extract_packages(index=index)
    packages = history.logs.extract_packages(index=index, packages=action_packages)

    if log.startswith("conda") and packages:
        env.history.packages.update_packages(packages=packages, source="conda")
    elif log.startswith("pip"):
        env.history.packages.update_packages(packages=packages, source="pip")
    return env


def _handle_conda_extra_log(
    env: Environment, history: History, index: int
) -> Environment:
    """Handle conda install, conda update --all and conda remove logs."""
    log = history.logs[index]
    channels = history.logs.extract_channels(index=index)
    handler = CondaHandler(env=env)
    if log.startswith("conda remove"):
        packages = history.logs.extra_removed_packages(index=index)
        handler.remove(packages=packages, channels=channels)
    else:
        packages = history.actions.extract_packages(index=index)
        if log.startswith("conda update --all"):
            handler.update_all(packages=packages, channels=channels)
        else:
            handler.install(packages=packages, channels=channels)
    env.history.logs[-1] = log
    return env


def _handle_pip_extra_log(
    env: Environment, history: History, index: int
) -> Environment:
    """Handle conda install, conda update --all and conda remove logs."""
    log = history.logs[index]
    handler = PipHandler(env=env)
    if log.startswith("pip uninstall"):
        packages = history.logs.extra_removed_packages(index=index)
        handler.remove(packages=packages)
    else:
        packages = history.actions.extract_packages(index=index)
        index_url = history.logs.extract_index_urls(index=index)
        handler.install(packages=packages, index_url=index_url)
    env.history.logs[-1] = log
    return env


def _handle_r_extra_log(env: Environment, history: History, index: int) -> Environment:
    log = history.logs[index]
    if "remove.packages(" in log:
        packages = history.logs.extra_removed_packages(index=index)
        RHandler(env=env).remove(packages=packages)
    else:
        package_names = [
            package_name
            for package_name in history.revisions.diffs[index]["r"]["upsert"]
        ]
        packages = Packages()
        for package_name in package_names:
            packages.append(history.revisions.packages[index]["r"][package_name])
        RHandler(env=env).install(packages=packages)
    return env


def _no_new_actions_in_remote(
    local_history: Optional[History], remote_history: History
) -> bool:
    """Handle case when no new action in the remote"""
    return is_ordered_subset(set=local_history.actions, subset=remote_history.actions)


def _no_new_actions_in_local(
    local_history: Optional[History], remote_history: History
) -> bool:
    """Handle case when there is no new action in local"""
    return is_ordered_subset(set=remote_history.actions, subset=local_history.actions)


def _actions_in_different_order(
    local_history: History, remote_history: History
) -> bool:
    """Handle case when action are in different order in remote and local"""
    return set(remote_history.actions).issubset(local_history.actions)
