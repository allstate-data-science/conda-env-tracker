"""Test the input/output of conda_env_tracker."""
# pylint: disable=redefined-outer-name
from pathlib import Path
import shutil

import pytest

from conda_env_tracker.gateways import io
from conda_env_tracker.errors import WindowsError
from conda_env_tracker.history import History, Channels, HistoryPackages, Logs, Actions


@pytest.fixture(scope="function")
def env_io():
    """Env io directory and fixture."""
    env_dir = Path(__file__).parent / "test-env-dir"
    yield io.EnvIO(env_dir)
    shutil.rmtree(env_dir)


@pytest.fixture(scope="function")
def remote_dir():
    """A remote directory fixture."""
    remote_dir = Path(__file__).parent / "test-remote-dir"
    if not remote_dir.exists():
        remote_dir.mkdir()
    yield remote_dir
    shutil.rmtree(remote_dir)


def test_get_history(env_io):
    """Test to get history from yaml file"""
    assert env_io.get_history() is None


def test_write_history_file(env_io):
    """Test to create history yaml file and test get history"""
    env_io.write_history_file(
        History(
            name="",
            channels=Channels([]),
            packages=HistoryPackages({}),
            logs=Logs([]),
            actions=Actions([]),
            debug=[],
        )
    )
    assert [] == env_io.get_history().channels
    assert {} == env_io.get_history().packages
    assert [] == env_io.get_history().logs
    assert [] == env_io.get_history().debug


def test_set_remote_dir(env_io, mocker):
    """Test to create remote setup file and assert remote dir path"""
    env_io.set_remote_dir(remote_dir="/nas/isg_prodops_work/connectedcar/riskmap")
    assert env_io.get_remote_dir() == "/nas/isg_prodops_work/connectedcar/riskmap"
    # User selects 'n' from prompt and does not update remote file
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=False)
    )
    env_io.set_remote_dir(remote_dir="riskmap")
    assert env_io.get_remote_dir() == "/nas/isg_prodops_work/connectedcar/riskmap"
    # User selects 'y' from prompt and updates file with new remote directory
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=True)
    )
    env_io.set_remote_dir(remote_dir="riskmap")
    assert env_io.get_remote_dir() == str(Path.cwd() / "riskmap")


def test_set_remote_dir_if_missing(env_io, mocker):
    """Test to create remote setup file using if_missing parameter. Error if file exists with a new path"""
    path = Path("/path/to/remote")
    env_io.set_remote_dir(remote_dir=path, if_missing=True)
    assert env_io.get_remote_dir() == str(path)
    new_path = Path("/new/path/to/new/remote")
    with pytest.raises(SystemExit):
        env_io.set_remote_dir(remote_dir=new_path, if_missing=True)
    env_io.set_remote_dir(remote_dir=new_path, if_missing=True, yes=True)
    assert env_io.get_remote_dir() == str(new_path)
    write_mock = mocker.patch("pathlib.Path.write_text")
    env_io.set_remote_dir(remote_dir=new_path, if_missing=True)
    write_mock.assert_not_called()


def test_copy_environment_from_local_to_remote(env_io, remote_dir):
    """Must copy local history file, env files. Does not copy remote.txt."""
    env_dir = env_io.env_dir
    expected_files = {"history.yaml", "conda-env.yaml"}
    for file_name in expected_files:
        (env_dir / file_name).touch()
    (env_dir / "remote.txt").touch()

    env_io.copy_environment(remote_dir)
    actual = {file.name for file in remote_dir.iterdir()}
    assert actual == expected_files


def test_overwrite_local_history_file(env_io, remote_dir):
    """Test overwriting the remote and local directory"""
    env_dir = env_io.env_dir
    env_file = env_dir / "history.yaml"
    env_file.write_text("conda_env_tracker local history")

    remote_io = io.EnvIO(remote_dir)
    remote_env_file = remote_dir / "history.yaml"
    remote_env_file.write_text("conda_env_tracker remote history")

    io.EnvIO.overwrite_local(local_io=env_io, remote_io=remote_io)
    assert env_file.exists()
    assert env_file.read_text() == "conda_env_tracker remote history"


def test_overwrite_install_r(env_io, remote_dir):
    env_dir = env_io.env_dir
    env_file = env_dir / "install.R"
    env_file.write_text("local install.R")

    remote_io = io.EnvIO(remote_dir)
    remote_env_file = remote_dir / "install.R"
    remote_env_file.write_text("conda_env_tracker remote install.R")

    io.EnvIO.overwrite_local(local_io=env_io, remote_io=remote_io)
    assert env_file.exists()
    assert env_file.read_text() == "conda_env_tracker remote install.R"


def test_overwrite_local_leave_local_file_when_not_in_remote(env_io, remote_dir):
    (env_io.env_dir / "local.txt").touch()

    remote_io = io.EnvIO(remote_dir)
    remote_env_file = remote_dir / "file.txt"
    remote_env_file.touch()

    io.EnvIO.overwrite_local(local_io=env_io, remote_io=remote_io)

    expected = {"local.txt", "file.txt"}
    actual = {file.name for file in env_io.env_dir.iterdir()}
    assert actual == expected


def test_copy_auto_no_existing_file(mocker):
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=False)
    )

    io.link_auto()

    symlink_mock.assert_called_once_with(
        io.SHELL_FILE, io.USER_CET_DIR / io.SHELL_FILE.name
    )


@pytest.mark.parametrize("response", [True, False])
def test_copy_auto_with_different_existing_file(mocker, response):
    package_shell_file = io.SHELL_FILE
    expected_contents = package_shell_file.read_text()

    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(side_effect=[expected_contents, "user file"]),
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=response)
    )

    io.link_auto()

    if response:
        symlink_mock.assert_called_once_with(
            io.SHELL_FILE, io.USER_CET_DIR / io.SHELL_FILE.name
        )
    else:
        symlink_mock.assert_not_called()


def test_copy_auto_with_same_existing_file(mocker):
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(return_value="string"),
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    prompt_mock = mocker.patch("conda_env_tracker.utils.prompt_yes_no")

    io.link_auto()

    prompt_mock.assert_not_called()
    symlink_mock.assert_not_called()


@pytest.mark.parametrize(
    "platform, bashrc_contents",
    [("linux", "file contents"), ("osx", f"Some file contents\n")],
)
def test_add_auto_to_bash_occurs(mocker, platform, bashrc_contents):
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    read_mock = mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(return_value=bashrc_contents),
    )
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.gateways.utils.get_platform_name",
        mocker.Mock(return_value=platform),
    )
    mocker.patch("os.path.getmtime", return_value=0)
    addition = f"\nsource {Path.home()}/.cet/cet-auto.sh\n"
    expected = bashrc_contents + addition

    io.add_auto_to_bash_config_file()

    write_mock.assert_called_once_with(expected)
    read_mock.assert_called_once_with()


@pytest.mark.parametrize(
    "platform, bashrc_contents",
    [
        ("linux", f"file contents\nsource {Path.home()}/.cet/cet-auto.sh\n"),
        ("osx", f"Some file contents\nsource {Path.home()}/.cet/cet-auto.sh\n"),
    ],
)
def test_add_auto_to_bash_skipped(mocker, platform, bashrc_contents):
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    read_mock = mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(return_value=bashrc_contents),
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.gateways.utils.get_platform_name",
        mocker.Mock(return_value=platform),
    )

    io.add_auto_to_bash_config_file()

    write_mock.assert_not_called()
    read_mock.assert_called_once_with()


def test_add_auto_when_bash_missing(mocker):
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    read_mock = mocker.patch("conda_env_tracker.gateways.io.Path.read_text")
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=False)
    )
    addition = f"\nsource {Path.home()}/.cet/cet-auto.sh\n"

    io.add_auto_to_bash_config_file()

    write_mock.assert_called_once_with(addition)
    read_mock.assert_not_called()


def test_do_not_add_auto_to_bash(mocker):
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    read_mock = mocker.patch("conda_env_tracker.gateways.io.Path.read_text")
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=False)
    )

    io.add_auto_to_bash_config_file()

    symlink_mock.assert_not_called()
    read_mock.assert_called_once_with()


def test_bash_config_windows_error(mocker):
    mocker.patch(
        "conda_env_tracker.gateways.utils.get_platform_name",
        mocker.Mock(return_value="win"),
    )
    with pytest.raises(WindowsError) as err:
        io.add_auto_to_bash_config_file()
    assert str(err.value) == "Windows is unsupported at this time"


def test_init(mocker,):
    prefix = "/path/to/prefix"
    bashrc_content = "content"
    mocker.patch("conda_env_tracker.gateways.io.Path.mkdir")
    mocker.patch("conda_env_tracker.gateways.io.sys.exec_prefix", prefix)
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=True)
    )
    unlink_mock = mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(return_value=bashrc_content),
    )

    io.init()

    unlink_mock.assert_called_once_with()
    symlink_mock.assert_called_once_with(
        Path(prefix) / "bin" / "cet", io.USER_CET_DIR / "cet"
    )

    expected = f'{bashrc_content}\nexport PATH="$PATH:{Path.home() / ".cet"}"\n'
    write_mock.assert_called_once_with(expected)


def test_init_nothing_exists(mocker):
    prefix = "/path/to/prefix"
    mocker.patch("conda_env_tracker.gateways.io.Path.mkdir")
    mocker.patch("conda_env_tracker.gateways.io.sys.exec_prefix", prefix)
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=False)
    )
    mocker.patch(
        "conda_env_tracker.utils.prompt_yes_no", mocker.Mock(return_value=True)
    )
    unlink_mock = mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    mocker.patch("conda_env_tracker.gateways.io.Path.read_text")

    io.init()

    unlink_mock.assert_not_called()
    symlink_mock.assert_called_once_with(
        Path(prefix) / "bin" / "cet", io.USER_CET_DIR / "cet"
    )

    expected = f'\nexport PATH="$PATH:{Path.home() / ".cet"}"\n'
    write_mock.assert_called_once_with(expected)


def test_init_already_in_bashrc(mocker):
    prefix = "/path/to/prefix"
    bashrc_content = f'content\nexport PATH="$PATH:{Path.home() / ".cet"}"\n'

    mocker.patch("conda_env_tracker.gateways.io.sys.exec_prefix", prefix)
    symlink_mock = mocker.patch("conda_env_tracker.gateways.io.os.symlink")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.exists", mocker.Mock(return_value=True)
    )
    unlink_mock = mocker.patch("conda_env_tracker.gateways.io.Path.unlink")
    write_mock = mocker.patch("conda_env_tracker.gateways.io.Path.write_text")
    mocker.patch(
        "conda_env_tracker.gateways.io.Path.read_text",
        mocker.Mock(return_value=bashrc_content),
    )

    io.init()

    unlink_mock.assert_called_once_with()
    symlink_mock.assert_called_once_with(
        Path(prefix) / "bin" / "cet", io.USER_CET_DIR / "cet"
    )
    write_mock.assert_not_called()
