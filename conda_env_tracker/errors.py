"""All cet errors."""

PUSH_ERROR_STR = """To {remote_dir}
 ! [rejected]        {local_dir} -> {remote_dir}
hint: Updates were rejected because the remote contains work that you do
hint: not have locally. You may want to first integrate the remote changes
hint: (e.g., 'cet pull ...') before pushing again."""


class Error(Exception):
    """The base exception for cet."""


class CondaEnvTrackerError(Error):
    """Conda-env-tracker related exception"""


class CondaEnvTrackerPackageNameError(CondaEnvTrackerError):
    """Conda-env-tracker package name error."""


class CondaEnvTrackerInstallError(CondaEnvTrackerError):
    """General exception for errors while installing."""


class CondaEnvTrackerCondaError(CondaEnvTrackerError):
    """Conda-env-tracker conda related exception"""


class CondaEnvTrackerChannelError(CondaEnvTrackerError):
    """Conda-env-tracker channel exception"""


class CondaEnvTrackerPushError(CondaEnvTrackerError):
    """Conda-env-tracker push exception"""


class CondaEnvTrackerParseHistoryError(CondaEnvTrackerError):
    """Conda-env-tracker parse history exception"""


class CondaEnvTrackerRemoteError(CondaEnvTrackerError):
    """Conda-env-tracker setup exception"""


class CondaEnvTrackerCreationError(CondaEnvTrackerError):
    """Conda-env-tracker environments were created with different commands"""


class CondaEnvTrackerHistoryNotFoundError(CondaEnvTrackerError):
    """Conda-env-tracker history file not found"""


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
