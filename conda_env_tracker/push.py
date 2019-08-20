"""Push environment from local to remote."""

import logging
from conda_env_tracker.env import Environment
from conda_env_tracker.gateways.io import EnvIO, USER_ENVS_DIR

from conda_env_tracker.utils import is_ordered_subset
from conda_env_tracker.errors import CondaEnvTrackerPushError, PUSH_ERROR_STR

logger = logging.getLogger(__name__)


def push(env: Environment) -> Environment:
    """Handle push to remote"""
    remote_dir = env.local_io.get_remote_dir()
    remote_io = EnvIO(env_directory=remote_dir)
    remote_history = remote_io.get_history()

    if remote_history == env.history:
        logger.info("Nothing to push.")
        return env

    if remote_history and (
        not is_ordered_subset(set=env.history.actions, subset=remote_history.actions)
        or not is_ordered_subset(set=env.history.logs, subset=remote_history.logs)
    ):
        raise CondaEnvTrackerPushError(
            PUSH_ERROR_STR.format(
                remote_dir=remote_dir, local_dir=USER_ENVS_DIR / env.name
            )
        )
    env.local_io.copy_environment(remote_dir)
    logger.info(f"Successfully push {env.name} to {remote_dir}")
    return env
