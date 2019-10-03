"""Test the utility functions."""
from pathlib import Path

import pytest

from conda_env_tracker.utils import prompt_yes_no
from conda_env_tracker.gateways.utils import (
    infer_remote_dir,
    run_command,
    print_package_list,
)
from conda_env_tracker.errors import (
    CondaEnvTrackerCondaError,
    CondaEnvTrackerHistoryNotFoundError,
    NotGitRepoError,
)
from conda_env_tracker.packages import Package


def test_current_infer_remote_dir(mocker):
    path = "/path/to/remote\n"
    run_mock = mocker.patch("conda_env_tracker.gateways.utils.subprocess.run")
    run_mock.configure_mock(**{"return_value.stdout": path})
    is_dir = mocker.patch("conda_env_tracker.gateways.utils.Path.is_dir")
    is_dir.configure_mock(return_value=False)

    with pytest.raises(NotGitRepoError):
        infer_remote_dir()

    is_dir.configure_mock(return_value=True)
    exists = mocker.patch("conda_env_tracker.gateways.utils.Path.exists")
    exists.configure_mock(return_value=False)

    with pytest.raises(CondaEnvTrackerHistoryNotFoundError):
        infer_remote_dir()

    exists.configure_mock(return_value=True)

    current_dir_remote_dir = infer_remote_dir()

    assert current_dir_remote_dir == Path(".cet")

    exists.configure_mock(side_effect=[False, True])

    git_remote_dir = infer_remote_dir()

    assert git_remote_dir == Path(path.strip()) / ".cet"


@pytest.mark.parametrize(
    "return_values", (["w", "V", "no"], ["n"], ["no"], ["yes"], ["y"])
)
def test_prompt_yes_no(mocker, return_values):
    patch = mocker.patch("conda_env_tracker.utils.input", side_effect=return_values)
    if return_values[-1] in ["n", "no"]:
        assert not prompt_yes_no(prompt_msg="")
    else:
        assert prompt_yes_no(prompt_msg="")
    assert len(patch.call_args_list) == len(return_values)


def test_prompt_yes_no_default(mocker):
    patch = mocker.patch("conda_env_tracker.utils.input", return_value="y")
    prompt_yes_no(prompt_msg="", default=True)
    patch.assert_called_with(" ([y]/n)? ")
    prompt_yes_no(prompt_msg="", default=False)
    patch.assert_called_with(" (y/[n])? ")


def test_exit_with_user_no(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.utils.run")
    attrs = {
        "return_value.return_code": 0,
        "return_value.stderr": "",
        "return_value.stdout": "Proceed ([y]/n)? n\n",
    }
    run_mock.configure_mock(**attrs)
    with pytest.raises(SystemExit):
        run_command(command="command", error=CondaEnvTrackerCondaError)


def test_print_package_list(mocker):
    sample_pkgs = {
        "conda": [
            Package("python", "3.7", "3.7.2"),
            Package("pandas", "*", "0.23_py37"),
        ],
        "pip": [Package("pytest", "*", "4.0")],
    }
    print_mock = mocker.patch("conda_env_tracker.gateways.utils.print")
    print_package_list(sample_pkgs)
    assert print_mock.call_args_list == [
        mocker.call("#conda:"),
        mocker.call("#   PACKAGE -> SPEC -> VERSION"),
        mocker.call("    python -> 3.7 -> 3.7.2"),
        mocker.call("    pandas -> * -> 0.23_py37"),
        mocker.call("#pip:"),
        mocker.call("#   PACKAGE -> SPEC -> VERSION"),
        mocker.call("    pytest -> * -> 4.0"),
    ]


def test_run_command_error_message(mocker, caplog):
    mocker.patch(
        "conda_env_tracker.gateways.utils.run",
        return_value=mocker.Mock(failed=True, stdout="", stderr="Error message"),
    )

    class CustomException(Exception):
        """Custom Exception"""

    with pytest.raises(CustomException) as err:
        run_command("command", CustomException)
    assert caplog.records[0].message == "command"
    assert str(err.value) == "Error message"
