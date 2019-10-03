"""The diff section of each revision in the history file."""

from typing import Optional

from conda_env_tracker.history.packages import PackageRevision
from conda_env_tracker.packages import Package, Packages


class Diff(dict):
    """The added, removed or updated packages for each revision."""

    @classmethod
    def create(cls, packages: Packages, dependencies: dict, source="conda"):
        """Create the diff for the first revision."""
        upsert = {}
        source_dependencies = dependencies.get(source, {})
        for package in packages:
            dependency = source_dependencies[package.name]
            upsert[package.name] = Package(
                name=package.name,
                spec=package.spec,
                version=dependency.version,
                build=dependency.build,
            )
        diffs = cls()
        diffs[source] = {"upsert": upsert}
        return diffs

    @classmethod
    def compute(
        cls,
        dependencies: dict,
        packages: PackageRevision,
        upsert_packages: Optional[Packages] = None,
        source: str = "conda",
    ):
        """Get the diff from the current revision before updating."""
        source_packages = packages.get(source, {})
        source_dependencies = dependencies.get(source, {})
        upsert = {}
        if upsert_packages:
            for package in upsert_packages:
                upsert[package.name] = package
        update, remove = cls._get_dependencies_diff(
            current_dependencies=source_dependencies, current_packages=source_packages
        )
        for key, value in update.items():
            if key not in upsert:
                upsert[key] = value
        diff = cls()
        diff[source] = {}
        if upsert:
            diff[source]["upsert"] = upsert
        if remove:
            diff[source]["remove"] = remove
        return diff

    @staticmethod
    def _get_dependencies_diff(current_dependencies: dict, current_packages: dict):
        removed = {}
        updated = {}
        for package_name, package in current_packages.items():
            if package_name not in current_dependencies:
                removed[package_name] = package
            elif package.version != current_dependencies[package_name].version:
                dependency = current_dependencies[package_name]
                updated[package_name] = Package(
                    name=package.name,
                    spec=package.spec,
                    version=dependency.version,
                    build=dependency.build,
                )
        return updated, removed

    def export(self):
        """Export to the history.yaml file."""
        output = {}
        for source, sections in self.items():
            output[source] = {}
            for section_name, packages in sections.items():
                section = []
                for package_name, package in packages.items():
                    if section_name == "remove" or source == "r":
                        section.append(package_name)
                    else:
                        section.append(
                            package.create_spec(
                                separator=PackageRevision.separators[source],
                                ignore_build=True,
                            )
                        )
                output[source][section_name] = section
        return output

    @classmethod
    def parse(cls, history_section: dict):
        """Parse the history.yaml file."""
        diff = cls()
        for source, sections in history_section.items():
            diff[source] = {}
            for section_name, package_specs in sections.items():
                diff[source][section_name] = {}
                for spec in package_specs:
                    if section_name == "remove" or source == "r":
                        package_name = spec
                        diff[source][section_name][package_name] = Package.from_spec(
                            package_name
                        )
                    else:
                        package_name, version = Package.separate_spec(spec)
                        diff[source][section_name][package_name] = Package(
                            name=package_name, spec=package_name, version=version
                        )
        return diff
