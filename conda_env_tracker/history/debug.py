"""Debug information for the environment."""
import datetime

from conda_env_tracker.gateways.conda import CONDA_VERSION
from conda_env_tracker.gateways.pip import get_pip_version
from conda_env_tracker.gateways.utils import get_platform_name


class Debug(list):
    """Debug information about each step in the history of the file."""

    def __init__(self, debug=None):
        list.__init__(self)
        if debug:
            self.extend(debug)

    @classmethod
    def create(cls, name: str):
        """Create the class with the first set of debug information."""
        debug = cls()
        debug.update(name=name)
        return debug

    def update(self, name: str) -> None:
        """Update with the current debug information."""
        pip_version = get_pip_version(name=name)
        self.append(
            {
                "platform": get_platform_name(),
                "conda_version": CONDA_VERSION,
                "pip_version": pip_version,
                "timestamp": str(datetime.datetime.now()),
            }
        )
