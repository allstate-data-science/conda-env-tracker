"""The command line interface to conda_env_tracker."""
# pylint: disable=function-redefined,invalid-name
import logging

import click
from colorama import Fore, Style

from conda_env_tracker import main, __version__
from conda_env_tracker.errors import CommandLineError

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--version",
    is_flag=True,
    default=False,
    help="Get the current conda env tracker version.",
)
def cli(ctx, version: bool = False):
    """The command line interface for conda env tracker."""
    if version:
        print(f"cet {__version__}")
    return ctx.invoked_subcommand


@cli.command()
@click.option(
    "--auto",
    "auto_arg",
    required=False,
    is_flag=True,
    default=False,
    help="Setup cet to automatically run push/pull in cet directories.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def init(auto_arg, yes):
    """Install the cet command line tool for all conda environments."""
    main.init(yes=yes)
    if auto_arg:
        main.setup_auto_shell_file()
        main.setup_auto_bash_config(yes=yes)


@cli.command()
@click.option(
    "--activate",
    is_flag=True,
    default=False,
    help="Automatically activate environments instead of asking if user wants to activate.",
)
@click.option(
    "--sync",
    "sync_arg",
    is_flag=True,
    default=False,
    help="Automatically sync environments instead of asking if user wants to sync.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
@click.option(
    "--ignore-bash-config",
    is_flag=True,
    default=False,
    help="Updates the shell file but makes no changes to the bash config file.",
)
def auto(activate, sync_arg, yes, ignore_bash_config):
    """Setup conda env tracker to automatically run push/pull in conda env tracker directories."""
    main.setup_auto_shell_file()
    if not ignore_bash_config:
        main.setup_auto_bash_config(activate=activate, sync=sync_arg, yes=yes)


@cli.command()
@click.argument("packages", nargs=-1)
@click.option(
    "--name",
    "-n",
    required=True,
    help="The name of the cet environment. Required for environment creation.",
)
@click.option(
    "--channel",
    "-c",
    multiple=True,
    help="Specify conda channels. Over-rides the channels in .condarc.",
)
@click.option(
    "--sync",
    "sync_arg",
    required=False,
    is_flag=True,
    default=False,
    help="Setup a .cet/ directory in the root of the git repo and sync automatically.",
)
@click.option(
    "--infer",
    required=False,
    is_flag=True,
    default=False,
    help="Infer the cet metadata for an existing conda environment.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
@click.option(
    "--strict-channel-priority",
    default=True,
    type=bool,
    help="Use strict channel priority (if True) or default channel priority (if False) with conda.",
)
def create(packages, name, channel, sync_arg, infer, yes, strict_channel_priority):
    """Create the software environment."""
    if infer:
        main.infer(name=name, specs=packages, channels=channel)
    else:
        main.create(
            name=name,
            specs=packages,
            channels=channel,
            yes=yes,
            strict_channel_priority=strict_channel_priority,
        )
    if sync_arg:
        main.setup_remote(name=name, yes=yes)
        main.push(name=name)


@cli.command()
@click.option("--name", "-n", help="The name of the conda env tracker environment.")
def rebuild(name):
    """Rebuild a conda env tracker environment. Deletes and creates the conda environment."""
    name = _infer_name_if_necessary(name)
    main.rebuild(name=name)


@cli.command(name="list")
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
def pkg_list(name):
    """List Packages in conda-env-tracker Environment"""
    name = _infer_name_if_necessary(name)
    main.pkg_list(name=name)


@cli.command()
@click.option("--name", "-n", help="The name of the conda env tracker environment.")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def remove(name, yes):
    """Remove a conda env tracker environment. Both the conda environment and any local files."""
    name = _infer_name_if_necessary(name)
    main.remove(name=name, yes=yes)


@cli.command()
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
def push(name):
    """Push the local environment to remote"""
    name = _infer_name_if_necessary(name)
    main.push(name=name)


@cli.command()
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def pull(name, yes):
    """Pull the remote environment into local"""
    name = _infer_name_if_necessary(name)
    main.pull(name=name, yes=yes)


@cli.command()
@click.argument("remote_dir", required=False, nargs=1)
@click.option(
    "--if-missing",
    is_flag=True,
    default=False,
    help="Only add the remote if it is missing. Used by cet auto.",
)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
def remote(remote_dir, if_missing, name):
    """Setup the remote directory to share the cet environment.

    If remote directory is not specified, then creates .cet in the root directory of the current git repo.
    """
    name = _infer_name_if_necessary(name)
    main.setup_remote(name=name, remote_dir=remote_dir, if_missing=if_missing)


@cli.command()
@click.option("--name", "-n", default=None, help="The name of the cet environment.")
@click.option(
    "--infer",
    is_flag=True,
    default=False,
    help="Infer remote dir from .cet/ dir or git repo root dir",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def sync(name, infer, yes):
    """Automatically pull and push environment changes (if necessary)."""
    name = _infer_name_if_necessary(name, infer=infer)
    main.sync(name=name, yes=yes)


@cli.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--channel",
    "-c",
    multiple=True,
    help="Conda channels. Appends to list of channels from creation.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
@click.option(
    "--strict-channel-priority",
    default=True,
    type=bool,
    help="Use strict channel priority (if True) or default channel priority (if False) with conda.",
)
def install(specs, name, channel, yes, strict_channel_priority):
    """Conda install (or update) packages."""
    name = _infer_name_if_necessary(name)
    main.conda_install(
        name=name,
        specs=specs,
        channels=channel,
        yes=yes,
        strict_channel_priority=strict_channel_priority,
    )


@cli.group()
def conda():
    """Access to cet supported conda command line functions."""


@cli.group()
def pip():
    """Access to cet supported pip command line functions."""


@cli.group(name="R")
def R():
    """Access to cet supported R command line functions."""


@cli.group()
def r():
    """Access to cet supported R command line functions."""


@cli.group()
def history():
    """Access to cet supported history command line functions."""


conda.add_command(create)
conda.add_command(install)


@conda.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--channel",
    "-c",
    multiple=True,
    help="Conda channels. Appends to list of channels from creation.",
)
@click.option("--all", is_flag=True, required=False)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
@click.option(
    "--strict-channel-priority",
    default=True,
    type=bool,
    help="Use strict channel priority (if True) or default channel priority (if False) with conda.",
)
def update(specs, name, channel, all, yes, strict_channel_priority):
    """Conda install (or update) packages."""
    name = _infer_name_if_necessary(name)
    main.conda_update(
        name=name,
        specs=specs,
        channels=channel,
        all=all,
        yes=yes,
        strict_channel_priority=strict_channel_priority,
    )


@conda.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--channel",
    "-c",
    multiple=True,
    help="Conda channels. Appends to list of channels from creation.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def remove(specs, name, channel, yes):
    """Conda remove packages."""
    # pylint: disable=function-redefined
    name = _infer_name_if_necessary(name)
    main.conda_remove(name=name, specs=specs, channels=channel, yes=yes)


@pip.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--index-url",
    multiple=True,
    help="Package index url (default is pypi mirror). Can list multiple index urls.",
)
@click.option("--custom", "url_path", required=False, type=str, default=None)
def install(specs, name, index_url, url_path):
    """Pip install (or update) packages."""
    # pylint: disable=function-redefined
    name = _infer_name_if_necessary(name)
    if index_url:
        main.pip_install(name=name, specs=specs, index_url=index_url)
    elif url_path:
        if len(specs) > 1:
            raise CommandLineError(
                "Cannot install multiple packages with custom install"
            )
        main.pip_custom_install(name=name, package=specs[0], url_path=url_path)
    elif not index_url and not url_path:
        main.pip_install(name=name, specs=specs)


@pip.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Answer yes to any questions. Required for non-interactive jobs.",
)
def remove(specs, name, yes):
    """Pip uninstall package"""
    # pylint: disable=function-redefined
    name = _infer_name_if_necessary(name)
    main.pip_remove(name=name, specs=specs, yes=yes)


pip.add_command(pip.commands["remove"], name="uninstall")


@R.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option("--command", "commands", required=True, multiple=True)
def install(specs, name, commands):
    """Install R packages using re-producible R commands.

    Each package must have a command associated with it to ensure reproducibility.

    \b
    Examples:
        cet R install jsonlite --command "install.packages('jsonlite')"
        cet R install jsonlite praise --command "install.packages('jsonlite')" --command "install.packages('praise')"
    """
    name = _infer_name_if_necessary(name)
    main.r_install(name=name, package_names=specs, commands=commands)


r.add_command(R.commands["install"])


@R.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False)
def remove(specs, name):
    """R remove package"""
    # pylint: disable=function-redefined
    name = _infer_name_if_necessary(name)
    main.r_remove(name=name, specs=specs)


r.add_command(R.commands["remove"])


@history.command()
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
def diff(name):
    """Show the difference between env packages and history packages."""
    name = _infer_name_if_necessary(name)
    diff_pkges = main.diff(name=name)
    for package in diff_pkges:
        if package.startswith("-"):
            print(Fore.RED + package)
        elif package.startswith("+"):
            print(Fore.GREEN + package)
    print(Style.RESET_ALL)


@history.command()
@click.argument("specs", nargs=-1)
@click.option("--name", "-n", required=False, help="The name of the cet environment.")
@click.option("--remove", "-r", multiple=True, help="Packages to remove.")
@click.option(
    "--channel",
    "-c",
    multiple=True,
    help="Conda channels to append to the cet metadata.",
)
def update(specs, name, remove, channel):
    """Update the history with added or removed packages."""
    # pylint: disable=redefined-outer-name,function-redefined
    name = _infer_name_if_necessary(name)
    if specs or remove:
        main.update_packages(name=name, specs=specs, remove=remove)
    if channel:
        main.update_channels(name=name, channels=channel)


def _infer_name_if_necessary(name, infer=None):
    if not name:
        name = main.get_env_name(infer=infer)
    return name
