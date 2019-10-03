"""Representing a conda environment.

https://pipenv.readthedocs.io/en/latest/basics/#example-pipfile-pipfile-lock
"""
from typing import Dict, Optional
import logging

import oyaml as yaml

from conda_env_tracker.channels import Channels
from conda_env_tracker.errors import (
    CondaEnvTrackerCondaError,
    CondaEnvTrackerInstallError,
    CondaEnvTrackerRemoteError,
)
from conda_env_tracker.gateways.conda import (
    conda_create,
    delete_conda_environment,
    get_all_existing_environment,
    get_dependencies,
    get_conda_channels,
    get_conda_create_command,
    update_conda_environment,
)
from conda_env_tracker.gateways.io import EnvIO, USER_ENVS_DIR
from conda_env_tracker.gateways.r import export_install_r, get_r_dependencies
from conda_env_tracker.history import (
    Actions,
    Debug,
    Diff,
    History,
    Logs,
    PackageRevision,
)
from conda_env_tracker.packages import Packages
from conda_env_tracker.pip import PipHandler
from conda_env_tracker.types import ListLike
from conda_env_tracker.utils import prompt_yes_no

logger = logging.getLogger(__name__)


class Environment:
    """Class representing a conda environment."""

    sources = ["conda", "pip", "r"]

    def __init__(
        self,
        name: str,
        history: Optional[History] = None,
        dependencies: Optional[dict] = None,
    ):
        self.name = name
        self.history = history
        self.local_io = EnvIO(env_directory=USER_ENVS_DIR / name)
        if dependencies:
            self.dependencies = dependencies
        else:
            self.dependencies = {}
            if self.history:
                self.dependencies = get_dependencies(name=self.name)
                if self.history.packages.get("r"):
                    self.dependencies["r"] = get_r_dependencies(name=self.name)
        if history:
            self.history.packages.update_versions(dependencies=self.dependencies)

    @classmethod
    def create(
        cls,
        name: str,
        packages: Packages,
        channels: ListLike = None,
        yes: bool = False,
        strict_channel_priority: bool = True,
    ):
        """Creating a conda environment from a list of packages."""
        if name == "base":
            raise CondaEnvTrackerCondaError(
                "Environment can not be created using default name base"
            )

        if name in get_all_existing_environment():
            message = (
                f"This environment {name} already exists. Would you like to replace it"
            )
            if prompt_yes_no(prompt_msg=message, default=False):
                delete_conda_environment(name=name)
                local_io = EnvIO(env_directory=USER_ENVS_DIR / name)
                if local_io.env_dir.exists():
                    local_io.delete_all()
            else:
                raise CondaEnvTrackerCondaError(f"Environment {name} already exists")
        logger.debug(f"creating conda env {name}")

        conda_create(
            name=name,
            packages=packages,
            channels=channels,
            yes=yes,
            strict_channel_priority=strict_channel_priority,
        )
        create_cmd = get_conda_create_command(
            name=name,
            packages=packages,
            channels=channels,
            strict_channel_priority=strict_channel_priority,
        )
        specs = Actions.get_package_specs(
            packages=packages, dependencies=get_dependencies(name=name)["conda"]
        )

        if not channels:
            channels = get_conda_channels()

        dependencies = get_dependencies(name=name)

        history = History.create(
            name=name,
            channels=Channels(channels),
            packages=PackageRevision.create(packages, dependencies=dependencies),
            logs=Logs(create_cmd),
            actions=Actions.create(
                name=name,
                specs=specs,
                channels=Channels(channels),
                strict_channel_priority=strict_channel_priority,
            ),
            diff=Diff.create(packages=packages, dependencies=dependencies),
            debug=Debug.create(name=name),
        )
        env = cls(name=name, history=history, dependencies=dependencies)
        env.export()

        return env

    @classmethod
    def read(cls, name: str):
        """read the environment from history file"""
        reader = EnvIO(env_directory=USER_ENVS_DIR / name)
        history = reader.get_history()
        return cls(name=name, history=history)

    @classmethod
    def infer(cls, name: str, packages: Packages, channels: ListLike = None):
        """create conda_env_tracker environment by inferring to existing conda environment"""
        if name == "base":
            raise CondaEnvTrackerCondaError(
                "Environment can not be created using default name base"
            )

        if name not in get_all_existing_environment():
            raise CondaEnvTrackerCondaError(
                f"Environment {name} can not be inferred, does not exist"
            )

        dependencies = get_dependencies(name=name)
        if "r-base" in dependencies["conda"]:
            dependencies["r"] = get_r_dependencies(name=name)

        user_packages = {"conda": Packages(), "pip": Packages()}
        for package in packages:
            if package.name in dependencies.get("conda", Packages()):
                user_packages["conda"].append(package)
            elif package.name in dependencies.get("pip", Packages()):
                user_packages["pip"].append(package)
            else:
                raise CondaEnvTrackerCondaError(
                    f"Environment {name} does not have {package.spec} installed"
                )

        conda_create_cmd = get_conda_create_command(
            name, user_packages["conda"], channels
        )

        specs = Actions.get_package_specs(
            packages=user_packages["conda"], dependencies=dependencies["conda"]
        )

        history = History.create(
            name=name,
            channels=Channels(channels),
            packages=PackageRevision.create(
                user_packages["conda"], dependencies=dependencies
            ),
            logs=Logs(conda_create_cmd),
            actions=Actions.create(name=name, specs=specs, channels=Channels(channels)),
            diff=Diff.create(
                packages=user_packages["conda"], dependencies=dependencies
            ),
            debug=Debug.create(name=name),
        )

        env = cls(name=name, history=history, dependencies=dependencies)
        if user_packages["pip"]:
            handler = PipHandler(env=env)
            handler.update_history_install(packages=user_packages["pip"])
            env = handler.env
        env.export()

        return env

    def export(self) -> None:
        """Export the conda environment and history."""
        self.local_io.write_history_file(history=self.history)
        self._export_packages()
        self._export_install_r_if_necessary()

    def rebuild(self) -> None:
        """Rebuild the conda environment."""
        logger.debug('If struggling to use an environment try "conda clean --all".')
        delete_conda_environment(name=self.name)
        update_conda_environment(env_dir=self.local_io.env_dir)
        self.update_dependencies()

    def remove(self, yes=False) -> None:
        """Remove the environment and history."""
        if yes or prompt_yes_no(
            f"Are you sure you want to remove the {self.name} environment",
            default=False,
        ):
            delete_conda_environment(name=self.name)
            try:
                remote_io = EnvIO(self.local_io.get_remote_dir())
            except CondaEnvTrackerRemoteError:
                remote_io = None
            self.local_io.delete_all()
            if remote_io and (
                yes
                or prompt_yes_no(
                    prompt_msg=f"Do you want to remove remote files in dir: {remote_io.env_dir}?"
                )
            ):
                remote_io.delete_all()

    def replace_history(self, history: History) -> None:
        """Replace with a new history."""
        self.history = history
        self.update_dependencies()

    def validate(self) -> None:
        """Check that all packages are installed correctly."""
        if self.history.packages.get("r"):
            self.update_dependencies(update_r_dependencies=True)
        else:
            self.update_dependencies()
        packages = Packages()
        for source in self.sources:
            packages += [
                package for package in self.history.packages.get(source, {}).values()
            ]
        self.validate_packages(packages)

    def append_channels(self, channels: ListLike) -> None:
        """Append channels to the list of channels in the history."""
        for channel in channels:
            if channel not in self.history.channels:
                self.history.channels.append(channel)
        self.local_io.write_history_file(history=self.history)

    def update_dependencies(self, update_r_dependencies=False):
        """Update the list of all conda, pip, and R dependencies installed."""
        self.dependencies = get_dependencies(name=self.name)
        if update_r_dependencies:
            self.dependencies["r"] = get_r_dependencies(name=self.name)

    def validate_packages(
        self, installed_packages: Packages = None, source: str = "conda"
    ):
        """Raise an error if a package was not installed correctly. If this command removes a package that
        was previously specified by the user, then warn that it has been removed and remove it from the history.
        """
        removed = []
        for package in self.history.packages.get(source, {}):
            if package not in self.dependencies.get(source, {}):
                removed.append(package)
        installed_names = set()
        if installed_packages:
            installed_names = {package.name for package in installed_packages}
        for package in removed:
            if package in installed_names:
                raise CondaEnvTrackerInstallError(
                    f'Package "{package}" was not installed.'
                )
            logger.warning(f'Package "{package}" was removed during the last command.')
            self.history.packages[source].pop(package)

    def _export_packages(self) -> None:
        """Export a conda env yaml file with only the packages with versions for switching platforms.

        Adding nodefaults to the channel list prevents conda env update statements from using the channels
        in the users .condarc file.
        """
        conda_environment = {
            "name": self.name,
            "channels": self.history.channels.export(),
        }
        if "nodefaults" not in conda_environment["channels"]:
            conda_environment["channels"].append("nodefaults")
        conda_environment["dependencies"] = []
        for package in self.history.packages.get("conda"):
            version = self.dependencies["conda"][package].version
            conda_environment["dependencies"].append(f"{package}={version}")
        conda_environment = self._add_pip_dependencies(conda_environment)
        contents = yaml.dump(conda_environment, default_flow_style=False)
        self.local_io.export_packages(contents=contents)

    def _add_pip_dependencies(self, conda_environment: Dict) -> Dict:
        """Add the pip dependencies to the environment yaml dict."""
        if self.history.packages.get("pip") and conda_environment.get("dependencies"):
            pip = {"pip": []}
            for name, package in self.history.packages["pip"].items():
                if package.spec_is_custom():
                    pip["pip"].append(package.spec)
                else:
                    version = self.dependencies["pip"][name].version
                    pip["pip"].append(f"{name}=={version}")
            conda_environment["dependencies"].append(pip)
        return conda_environment

    def _export_install_r_if_necessary(self) -> None:
        """Export an install.R file that can be used to install the same R packages and versions."""
        if self.history.packages.get("r"):
            install_r = export_install_r(
                packages=Packages(
                    [package for package in self.history.packages["r"].values()]
                )
            )
            self.local_io.export_install_r(install_r)
        else:
            self.local_io.delete_install_r()
