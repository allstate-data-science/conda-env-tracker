"""All habitat errors."""

PUSH_ERROR_STR = """To {remote_dir}
 ! [rejected]        {local_dir} -> {remote_dir}
hint: Updates were rejected because the remote contains work that you do
hint: not have locally. You may want to first integrate the remote changes
hint: (e.g., 'habitat pull ...') before pushing again."""


class Error(Exception):
    """The base exception for habitat."""


class CondaEnvTrackerError(Error):
    """CondaEnvTracker related exception"""


class CondaEnvTrackerPackageNameError(CondaEnvTrackerError):
    """CondaEnvTracker package name error."""


class CondaEnvTrackerInstallError(CondaEnvTrackerError):
    """General exception for errors while installing."""


class CondaEnvTrackerCondaError(CondaEnvTrackerError):
    """CondaEnvTracker conda related exception"""


class CondaEnvTrackerChannelError(CondaEnvTrackerError):
    """CondaEnvTracker channel exception"""


class CondaEnvTrackerPushError(CondaEnvTrackerError):
    """CondaEnvTracker push exception"""


class CondaEnvTrackerPullError(CondaEnvTrackerError):
    """CondaEnvTracker pull exception"""


class CondaEnvTrackerParseHistoryError(CondaEnvTrackerError):
    """CondaEnvTracker parse history exception"""


class CondaEnvTrackerRemoteError(CondaEnvTrackerError):
    """CondaEnvTracker setup exception"""


class CondaEnvTrackerCreationError(CondaEnvTrackerError):
    """CondaEnvTracker environments were created with different commands"""


class CondaEnvTrackerHistoryNotFoundError(CondaEnvTrackerError):
    """CondaEnvTracker history file not found"""


class CondaEnvTrackerUpgradeError(CondaEnvTrackerError):
    """Error while upgrading habitat history file"""


class NotGitRepoError(CondaEnvTrackerError):
    """Directory is not in a git repo"""


class BashrcNotFoundError(CondaEnvTrackerError):
    """Bashrc file not found"""


class WindowsError(CondaEnvTrackerError):
    """Windows is not currently supported"""


class PipInstallError(CondaEnvTrackerInstallError):
    """Pip install failed"""


class PipRemoveError(CondaEnvTrackerError):
    """Pip remove failed"""


class RError(CondaEnvTrackerError):
    """Errors using R."""


class DateError(CondaEnvTrackerError):
    """Errors passing dates."""


class JupyterKernelInstallError(CondaEnvTrackerError):
    """Error while installing Jupyter Kernel"""


class CommandLineError(CondaEnvTrackerError):
    """Error while parsing commands"""
