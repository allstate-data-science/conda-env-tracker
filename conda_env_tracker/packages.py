"""Keeping track of packages (as opposed to dependencies, which just come along for the ride)."""
import re

from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

from conda_env_tracker.types import ListLike


class Package:
    """The metadata about each package."""

    def __init__(self, name, spec=None, version=None, build=None):
        self.name = name
        self.spec = spec
        self.version = version
        self.build = build

    @classmethod
    def from_spec(cls, spec):
        """Generate a package from user input package name or spec."""
        separated = cls.separate_spec(spec)
        name = separated[0]
        if separated:
            return cls(name=name, spec=spec)
        return cls(name=name, spec=name)

    @staticmethod
    def separate_spec(spec: str) -> list:
        """Separate the package name from the version in the spec."""
        return re.split("[!<=>]+", spec, maxsplit=1)

    def spec_is_name(self):
        """Check if the spec is just the package name."""
        return self.spec == self.name

    def get_version_from_spec(self, ignore_build=False) -> Optional[str]:
        """If there is a version in the spec, then get the version.

        If there is a build string in the spec, then ignore_build=True will return only the version.
        """
        separated = self.separate_spec(self.spec)
        if len(separated) == 2:
            version = separated[1]
            if ignore_build:
                return self.separate_spec(version)[0]
            return version
        return None

    def create_spec(self, separator="=", ignore_build=False) -> str:
        """Create the spec from the version and (optionally) build."""
        if not ignore_build and self.build:
            return separator.join([self.name, self.version, self.build])
        return self.name + separator + self.version

    def spec_is_custom(self) -> bool:
        """Custom urls was used to install."""
        return not self.spec.startswith(self.name)

    def __eq__(self, other):
        try:
            if self.version and self.version != other.version:
                return False
            if self.build and self.build != other.build:
                return False
            return self.name == other.name and self.spec == other.spec
        except AttributeError:
            return False

    def __repr__(self):
        return f"Package(name={self.name}, spec={self.spec}, version={self.version}, build={self.build})"


class Packages(list):
    """A list of instances of Package."""

    def __init__(
        self, packages: Union[List[Package], Tuple[Package, ...], Package] = None
    ):
        if packages:
            if isinstance(packages, Package):
                packages = [packages]
            list.__init__(self, packages)
        else:
            list.__init__(self)

    @classmethod
    def from_specs(cls, specs: Union[ListLike, str]):
        """Make a list of Package instances from the package spec."""
        packages = cls()
        if isinstance(specs, str):
            packages.append(Package.from_spec(specs))
        else:
            for spec in specs:
                packages.append(Package.from_spec(spec))
        return packages

    def append_spec(self, spec: str):
        """Append an instance of the Package using the spec."""
        self.append(Package.from_spec(spec))


def get_packages(env: "Environment") -> Dict[str, List[Package]]:
    """This function gets the package information for all user requested packages in an environment."""
    output_packages = defaultdict(list)
    for source, packages in env.history.packages.items():
        for name, package in packages.items():
            dep = env.dependencies[source][name]
            output_packages[source].append(
                Package(name, package.spec, dep.version, dep.build)
            )
    return output_packages
