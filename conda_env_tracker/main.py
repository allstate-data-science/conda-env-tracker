"""User facing interface to all internal functionality. Each function is equivalent to the command line interface."""

from datetime import date
import logging
import os
from typing import Optional, Union

from conda_env_tracker.env import Environment
from conda_env_tracker.push import push as _push
from conda_env_tracker.pull import pull as _pull

from conda_env_tracker.conda import CondaHandler
from conda_env_tracker.errors import CondaEnvTrackerHistoryNotFoundError
from conda_env_tracker.gateways.conda import get_active_conda_env_name
from conda_env_tracker.gateways.jupyter import jupyter_kernel_install_query
from conda_env_tracker.gateways.io import (
    add_auto_to_bash_config_file,
    link_auto,
    EnvIO,
    init as _init,
    USER_ENVS_DIR,
)
from conda_env_tracker.gateways.utils import infer_remote_dir, print_package_list
from conda_env_tracker.history import History
from conda_env_tracker.packages import get_packages, Package, Packages
from conda_env_tracker.pip import PipHandler, PIP_DEFAULT_INDEX_URL
from conda_env_tracker.r import RHandler
from conda_env_tracker.specs import process_specs, process_r_specs
from conda_env_tracker.types import ListLike, PathLike
from conda_env_tracker.utils import prompt_yes_no
from conda_env_tracker.validate import (
    check_pip,
    check_r_base_package,
    validate_remote_if_missing,
)

TODAY = str(date.today())
logger = logging.getLogger(__name__)


def init(yes: bool = False):
    """Install the cet command line tool for all conda environments."""
    _init(yes=yes)


def create(
    name: str,
    specs: ListLike,
    channels: ListLike = None,
    yes: bool = False,
    strict_channel_priority: bool = True,
) -> Environment:
    """create conda environment given environment name and packages to install"""
    cleaned = process_specs(specs)
    env = Environment.create(
        name=name,
        packages=cleaned,
        channels=channels,
        yes=yes,
        strict_channel_priority=strict_channel_priority,
    )
    env.export()
    if not yes:
        jupyter_kernel_install_query(name=name, packages=cleaned)
    return env


def infer(name: str, specs: ListLike, channels: ListLike = None) -> Environment:
    """infer environment from existing conda environment"""
    cleaned = process_specs(specs)
    env = Environment.infer(name=name, packages=cleaned, channels=channels)
    return env


def rebuild(name: str) -> Environment:
    """Rebuild the conda environment."""
    env = Environment.read(name=name)
    env.rebuild()
    return env


def remove(name: str, yes=False) -> None:
    """Remove the cet environment. Conda environment and any associated files."""
    env = Environment.read(name=name)
    env.remove(yes=yes)


def push(name: str) -> Environment:
    """Push the local changes to remote"""
    env = Environment.read(name=name)
    return _push(env=env)


def pull(name: str, yes: bool = False) -> Environment:
    """Pull the remote changes to local"""
    env = Environment.read(name=name)
    return _pull(env=env, yes=yes)


def sync(name: str, yes: bool = False) -> Environment:
    """Automatically pull and push any changes needed"""
    env = Environment.read(name=name)
    env = _pull(env=env, yes=yes)
    return _push(env=env)


def pkg_list(name: str) -> dict:
    """A function to print the list of packages in the environment"""
    env = Environment.read(name=name)
    packages = get_packages(env)
    print_package_list(packages)
    return packages


def conda_install(
    name: str,
    specs: ListLike,
    channels: ListLike = None,
    yes: bool = False,
    strict_channel_priority: bool = True,
) -> Environment:
    """Install conda packages into the environment."""
    env = Environment.read(name=name)
    cleaned = process_specs(specs)
    CondaHandler(env=env).install(
        packages=cleaned,
        channels=channels,
        yes=yes,
        strict_channel_priority=strict_channel_priority,
    )
    if not yes:
        jupyter_kernel_install_query(name=name, packages=cleaned)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def conda_update(
    name: str,
    specs: ListLike = (),
    channels: ListLike = None,
    all=False,
    yes: bool = False,
    strict_channel_priority: bool = True,
) -> Environment:
    """Install conda packages into the environment."""
    env = Environment.read(name=name)
    cleaned = process_specs(specs)
    if all:
        CondaHandler(env=env).update_all(
            packages=cleaned,
            channels=channels,
            yes=yes,
            strict_channel_priority=strict_channel_priority,
        )
    else:
        CondaHandler(env=env).install(
            packages=cleaned,
            channels=channels,
            yes=yes,
            strict_channel_priority=strict_channel_priority,
        )
    _ask_user_to_sync(name=name, yes=yes)
    return env


def conda_remove(
    name: str, specs: ListLike, channels: ListLike = None, yes: bool = False
) -> Environment:
    """Remove conda packages into the environment."""
    env = Environment.read(name=name)
    cleaned = process_specs(specs)
    CondaHandler(env=env).remove(packages=cleaned, channels=channels, yes=yes)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def pip_install(
    name: str,
    specs: ListLike,
    index_url: Union[str, ListLike] = PIP_DEFAULT_INDEX_URL,
    yes: bool = False,
) -> Environment:
    """Install pip packages into the environment."""
    env = Environment.read(name=name)
    check_pip(env=env)
    cleaned = process_specs(specs, check_custom=True)
    PipHandler(env=env).install(packages=cleaned, index_url=index_url)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def pip_remove(name: str, specs: ListLike, yes: bool = False) -> Environment:
    """Remove pip packages including custom packages"""
    env = Environment.read(name=name)
    check_pip(env=env)
    cleaned = process_specs(specs)
    PipHandler(env=env).remove(packages=cleaned, yes=yes)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def pip_custom_install(
    name: str, package: str, url_path: str, yes: bool = False
) -> Environment:
    """Install custom pip package"""
    env = Environment.read(name=name)
    check_pip(env=env)
    cleaned = Package(name=package.lower(), spec=url_path)
    PipHandler(env=env).custom_install(package=cleaned)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def r_install(
    name: str, package_names: ListLike, commands: ListLike, yes: bool = False
) -> Environment:
    """Install R packages with corresponding R command."""
    env = Environment.read(name=name)
    check_r_base_package(env=env)
    packages = process_r_specs(package_names=package_names, commands=commands)
    RHandler(env=env).install(packages=packages)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def r_remove(name: str, specs=ListLike, yes: bool = False) -> Environment:
    """R remove spec"""
    env = Environment.read(name=name)
    check_r_base_package(env=env)
    packages = Packages.from_specs(specs)
    RHandler(env=env).remove(packages=packages)
    _ask_user_to_sync(name=name, yes=yes)
    return env


def setup_remote(
    name: str,
    remote_dir: Optional[PathLike] = None,
    if_missing: bool = False,
    yes: bool = False,
) -> None:
    """setup remote directory for push and pull"""
    if not remote_dir:
        remote_dir = infer_remote_dir(check_history_exists=False)
    env_io = EnvIO(env_directory=USER_ENVS_DIR / name)
    validate_remote_if_missing(
        env_io=env_io, remote_dir=remote_dir, yes=yes, if_missing=if_missing
    )
    env_io.set_remote_dir(remote_dir=remote_dir, yes=yes)


def setup_auto_shell_file() -> None:
    """Setup the automatic use of conda env tracker push/pull when navigating to git repos"""
    # pylint: disable=redefined-outer-name
    link_auto()


def setup_auto_bash_config(
    activate: bool = False, sync: bool = False, yes: bool = False
):
    """Setup bash config to automatically use conda env tracker push/pull when navigating to git repos"""
    # pylint: disable=redefined-outer-name
    add_auto_to_bash_config_file(activate=activate, sync=sync, yes=yes)


def diff(name: str) -> ListLike:
    """Get the difference between history yaml and local conda environment"""
    env = Environment.read(name=name)
    env_reader = EnvIO(env_directory=USER_ENVS_DIR / name)
    version_diff_pkges, new_pkges, missing_pkges = History.history_diff(
        env_name=name, env=env, env_reader=env_reader
    )
    return missing_pkges + version_diff_pkges + new_pkges


def update_packages(name: str, specs: ListLike, remove: ListLike) -> Environment:
    """Update the history with local packages installed without cet cli."""
    # pylint: disable=redefined-outer-name
    env = Environment.read(name=name)
    handler = CondaHandler(env=env)
    if remove:
        cleaned_remove = process_specs(remove)
        handler.update_history_remove(packages=cleaned_remove)
    if specs:
        cleaned = process_specs(specs)
        handler.update_history_install(packages=cleaned)
    env.export()
    return env


def update_channels(name: str, channels: ListLike) -> Environment:
    """Add channels to the cet for future installs."""
    env = Environment.read(name=name)
    env.append_channels(channels)
    return env


def get_env_name(infer: bool = False) -> str:
    """Get the name of the environment either from current conda environment, from remote directory,
    or inferred from git repo.
    """
    # pylint: disable=redefined-outer-name
    if not infer:
        return get_active_conda_env_name()
    try:
        remote_dir = infer_remote_dir()
        history = EnvIO(env_directory=remote_dir).get_history()
        return history.name
    except CondaEnvTrackerHistoryNotFoundError as err:
        raise CondaEnvTrackerHistoryNotFoundError(
            f"Cannot infer name from history, often resolved by passing the name argument. Full error: {str(err)}"
        )


def _ask_user_to_sync(name: str, yes: bool = False):
    """If the user is updating the environment and using the auto functionality then ask if they want to sync."""
    if (
        not yes
        and os.environ.get("CET_AUTO") == "0"
        and _remote_dir_is_set(name=name)
        and prompt_yes_no(f"Conda-env-tracker sync changes to '{name}' environment")
    ):
        sync(name=name, yes=True)


def _remote_dir_is_set(name: str) -> bool:
    """Check if the remote directory has been setup for the cet environment."""
    env_io = EnvIO(env_directory=USER_ENVS_DIR / name)
    return env_io.is_remote_dir_set()
