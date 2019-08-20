"""Test the command line interface."""
import string

from click.testing import CliRunner

from colorama import Fore, Style
from hypothesis import given, settings, strategies as st

import pytest

from conda_env_tracker.cmdline import cli

settings(deadline=None)
TEXT = st.text(string.ascii_letters + string.digits, min_size=1)


@given(
    name=TEXT,
    specs=st.one_of(st.tuples(), st.tuples(TEXT), st.tuples(TEXT, TEXT)),
    channels=st.one_of(st.tuples(), st.tuples(TEXT), st.tuples(TEXT, TEXT)),
)
def test_create(name, specs, channels, mocker):
    command = ["conda", "create", "--name", name]
    command += [package for package in specs]
    if channels:
        command += ("--channel " + " --channel ".join(channels)).split()
    create_mock = mocker.patch("conda_env_tracker.main.create")
    runner = CliRunner()
    result = runner.invoke(cli, command)
    create_mock.assert_called_once_with(
        name=name,
        specs=specs,
        channels=channels,
        yes=False,
        strict_channel_priority=True,
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        (
            "conda install --name test python=3.6 numpy".split(),
            {"name": "test", "specs": ("python=3.6", "numpy"), "channels": ()},
        ),
        (
            "conda install python=3.7 pandas".split(),
            {"name": "inferred", "specs": ("python=3.7", "pandas"), "channels": ()},
        ),
    ],
)
def test_conda_install(mocker, command, expected):
    install_mock = mocker.patch("conda_env_tracker.main.conda_install")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    install_mock.assert_called_once_with(
        name=expected["name"],
        specs=expected["specs"],
        channels=expected["channels"],
        yes=False,
        strict_channel_priority=True,
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        (
            "pip install --name test python=3.6 numpy".split(),
            {"name": "test", "specs": ("python=3.6", "numpy"), "index_url": ()},
        ),
        (
            "pip install python=3.7 pandas".split(),
            {"name": "inferred", "specs": ("python=3.7", "pandas"), "index_url": ()},
        ),
        (
            "pip install python=3.7 xgboost --index-url a-url".split(),
            {
                "name": "inferred",
                "specs": ("python=3.7", "xgboost"),
                "index_url": ("a-url",),
            },
        ),
        (
            "pip install python=3.7 pytest --index-url first-url --index-url second-url".split(),
            {
                "name": "inferred",
                "specs": ("python=3.7", "pytest"),
                "index_url": ("first-url", "second-url"),
            },
        ),
    ],
)
def test_pip_install(mocker, command, expected):
    install_mock = mocker.patch("conda_env_tracker.main.pip_install")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    if expected["index_url"]:
        install_mock.assert_called_once_with(
            name=expected["name"],
            specs=expected["specs"],
            index_url=expected["index_url"],
        )
    else:
        install_mock.assert_called_once_with(
            name=expected["name"], specs=expected["specs"]
        )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        (
            "remote --name explicit_name /nas/isg_prodops_work/connectedcar/riskmap".split(),
            {
                "name": "explicit_name",
                "remote_dir": "/nas/isg_prodops_work/connectedcar/riskmap",
            },
        ),
        (
            "remote /nas/isg_prodops_work/connectedcar/riskmap".split(),
            {
                "name": "inferred_name",
                "remote_dir": "/nas/isg_prodops_work/connectedcar/riskmap",
            },
        ),
        ("remote".split(), {"name": "inferred_name", "remote_dir": None}),
    ],
)
def test_setup_remote(mocker, command, expected):
    setup_mock = mocker.patch("conda_env_tracker.main.setup_remote")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred_name")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    setup_mock.assert_called_once_with(
        name=expected["name"], remote_dir=expected["remote_dir"], if_missing=False
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        ("history diff --name test".split(), {"name": "test"}),
        ("history diff".split(), {"name": "inferred"}),
    ],
)
def test_diff(mocker, command, expected):
    setup_mock = mocker.patch(
        "conda_env_tracker.main.diff",
        mocker.Mock(
            return_value=["-pandas=0.22=py36", "+pandas=0.23=py36", "+pytest=0.22=py36"]
        ),
    )
    print_mock = mocker.patch("conda_env_tracker.cmdline.print")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    setup_mock.assert_called_once_with(name=expected["name"])
    assert print_mock.call_args_list == [
        mocker.call(Fore.RED + "-pandas=0.22=py36"),
        mocker.call(Fore.GREEN + "+pandas=0.23=py36"),
        mocker.call(Fore.GREEN + "+pytest=0.22=py36"),
        mocker.call(Style.RESET_ALL),
    ]
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        (
            "history update --name test pandas --remove pytest --remove pylint".split(),
            {
                "name": "test",
                "specs": ("pandas",),
                "remove": ("pytest", "pylint"),
                "channel": (),
            },
        ),
        (
            "history update pandas --remove pytest --remove pylint".split(),
            {
                "name": "inferred",
                "specs": ("pandas",),
                "remove": ("pytest", "pylint"),
                "channel": (),
            },
        ),
        (
            "history update pandas".split(),
            {"name": "inferred", "specs": ("pandas",), "remove": (), "channel": ()},
        ),
        (
            "history update --remove pytest --remove pylint".split(),
            {
                "name": "inferred",
                "specs": (),
                "remove": ("pytest", "pylint"),
                "channel": (),
            },
        ),
        (
            "history update --channel conda-main --channel conda-forge".split(),
            {
                "name": "inferred",
                "specs": (),
                "remove": (),
                "channel": ("conda-main", "conda-forge"),
            },
        ),
    ],
)
def test_update(mocker, command, expected):
    package_mock = mocker.patch("conda_env_tracker.main.update_packages")
    channel_mock = mocker.patch("conda_env_tracker.main.update_channels")

    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    if expected["specs"] or expected["remove"]:
        package_mock.assert_called_once_with(
            name=expected["name"], specs=expected["specs"], remove=expected["remove"]
        )
    else:
        package_mock.assert_not_called()
    if expected["channel"]:
        channel_mock.assert_called_once_with(
            name=expected["name"], channels=expected["channel"]
        )
    else:
        channel_mock.assert_not_called()
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, name", [("push --name test".split(), "test"), (["push"], "inferred")]
)
def test_push(mocker, command, name):
    push_mock = mocker.patch("conda_env_tracker.main.push")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    push_mock.assert_called_once_with(name=name)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        ("pull --name test".split(), {"name": "test", "yes": False}),
        ("pull --name test --yes".split(), {"name": "test", "yes": True}),
        (["pull"], {"name": "inferred", "yes": False}),
    ],
)
def test_pull(mocker, command, expected):
    pull_mock = mocker.patch("conda_env_tracker.main.pull")
    mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value="inferred")
    )
    runner = CliRunner()
    result = runner.invoke(cli, command)
    pull_mock.assert_called_once_with(**expected)
    assert result.exit_code == 0


def test_sync_implicit(mocker):
    name = "name_of_env"

    name_mock = mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value=name)
    )
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    name_mock.assert_called_once_with(infer=False)
    sync_mock.assert_called_once_with(name=name, yes=False)


@pytest.mark.parametrize(
    "infer, yes", [(False, False), (False, True), (True, False), (True, True)]
)
def test_sync_inferred_name(mocker, infer, yes):
    name = "name_of_env"

    name_mock = mocker.patch(
        "conda_env_tracker.main.get_env_name", mocker.Mock(return_value=name)
    )
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    runner = CliRunner()
    command = ["sync"]
    if infer:
        command.append("--infer")
    if yes:
        command.append("--yes")
    result = runner.invoke(cli, command)

    assert result.exit_code == 0
    name_mock.assert_called_once_with(infer=infer)
    sync_mock.assert_called_once_with(name=name, yes=yes)


def test_sync_name_passed(mocker):
    name = "name_of_env"

    name_mock = mocker.patch("conda_env_tracker.main.get_env_name")
    sync_mock = mocker.patch("conda_env_tracker.main.sync")

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--name", name])

    assert result.exit_code == 0
    name_mock.assert_not_called()
    sync_mock.assert_called_once_with(name=name, yes=False)
