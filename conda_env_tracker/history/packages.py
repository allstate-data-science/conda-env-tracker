"""The user specific packages for the current revision of the environment."""

from conda_env_tracker.packages import Packages, Package


class PackageRevision(dict):
    """Importing and exporting user specified package information in the history."""

    sources = ["conda", "pip"]
    separators = {"conda": "=", "pip": "==", "r": "="}

    def update_packages(self, packages: Packages, source="conda") -> None:
        """Update the conda packages."""
        self[source] = self.get(source, {})
        self._update_packages(self[source], packages)

    @staticmethod
    def _update_packages(existing: dict, new: Packages) -> None:
        for package in new:
            existing[package.name] = package

    def update_versions(self, dependencies: dict) -> None:
        """Update the versions (and possible build strings) of the packages."""
        for source_name, source in self.items():
            source_dependencies = dependencies.get(source_name, {})
            for package_name, package in source.items():
                dependency = source_dependencies.get(
                    package_name, Package(name=package_name)
                )
                package.version = dependency.version
                if dependency.build:
                    package.build = dependency.build

    def remove_packages(self, packages: Packages, source="conda") -> None:
        """Remove packages."""
        for package in packages:
            self[source].pop(package.name, None)

    @classmethod
    def create(cls, packages: Packages, dependencies: dict):
        """Create an instance of the HistoryPackages class from a list of packages."""
        packages_instance = cls()
        packages_instance.update_packages(packages=packages)
        packages_instance.update_versions(dependencies=dependencies)
        return packages_instance

    @classmethod
    def parse(cls, history_section: dict):
        """Parse the history file and create the packages."""
        packages_instance = cls()
        for source, packages in history_section.items():
            source_packages = Packages()
            for name, spec in packages.items():
                if spec == "*":
                    source_packages.append_spec(name)
                else:
                    source_packages.append(Package(name, spec))
            packages_instance.update_packages(packages=source_packages, source=source)
        return packages_instance

    def export(self) -> dict:
        """Export the packages with '*' for version if none was specified."""
        output = {}
        for source, packages in self.items():
            source_packages = {}
            for name, info in packages.items():
                if info.spec_is_name():
                    source_packages[name] = "*"
                else:
                    source_packages[name] = info.spec
            if source_packages:
                output[source] = source_packages
        return output
