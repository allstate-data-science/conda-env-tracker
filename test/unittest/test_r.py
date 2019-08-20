"""Test the RHandler"""
import copy

import pytest

from conda_env_tracker.packages import Package, Packages
from conda_env_tracker.r import RHandler


def test_custom_r_install(setup_env, mocker):
    command = 'install.packages("h2o")'
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])

    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False, "return_value.stderr": ""})
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        mocker.Mock(return_value={"h2o": "3.24.0.3"}),
    )
    h2o = Package("h2o", command)
    packages = Packages([h2o])

    RHandler(env=env).install(packages=packages)
    expected["logs"].append(f"R --quiet --vanilla -e '{command}'")
    expected["packages"]["r"] = {"h2o": h2o}
    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == expected["logs"][-1]

    actual_install_r = (env_io.env_dir / "install.R").read_text()
    assert actual_install_r == command


def test_two_same_package_custom_r_install(setup_env, mocker):
    """Test that the second command replaces the first command (and updates the version of the package)"""
    custom_command_h2o_1 = 'install.packages("h2o")'
    custom_command_h2o_2 = 'install.packages("h2o", type="source", repos=(c("http://h2o-release.s3.amazonaws.com/h2o/latest_stable_R")))'
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])

    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False, "return_value.stderr": ""})
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        side_effect=[
            {"h2o": Package("h2o", "h2o", "3.4.0.1")},
            {"h2o": Package("h2o", "h2o", "3.24.0.5")},
        ],
    )

    h2o_1 = Package("h2o", custom_command_h2o_1)
    h2o_2 = Package("h2o", custom_command_h2o_2)

    packages_1 = Packages([h2o_1])
    packages_2 = Packages([h2o_2])

    RHandler(env=env).install(packages=packages_1)
    RHandler(env=env).install(packages=packages_2)

    expected["logs"].append(f"R --quiet --vanilla -e '{custom_command_h2o_1}'")
    expected["logs"].append(f"R --quiet --vanilla -e '{custom_command_h2o_2}'")
    expected["packages"]["r"] = {"h2o": h2o_2}
    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == expected["logs"][-1]

    actual_install_r = (env_io.env_dir / "install.R").read_text()
    assert actual_install_r == custom_command_h2o_2


def test_two_custom_r_install(setup_env, mocker):
    """Test that the second custom command replaces the first command (and updates the version of the package)"""
    custom_command_h2o = 'install.packages("h2o")'
    custom_command_trelliscopejs = (
        'library("devtools"); install_github("hafen/trelliscopejs")'
    )
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])

    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False, "return_value.stderr": ""})
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        return_value={
            "h2o": Package("h2o", "h2o", "3.4.0.1"),
            "trelliscopejs": Package("trelliscopejs", "trelliscopejs", "0.1.7"),
        },
    )

    h2o = Package("h2o", custom_command_h2o)
    trelliscopejs = Package("trelliscopejs", custom_command_trelliscopejs)

    RHandler(env=env).install(packages=Packages([h2o]))
    RHandler(env=env).install(packages=Packages([trelliscopejs]))

    expected["logs"].append(f"R --quiet --vanilla -e '{custom_command_h2o}'")
    expected["logs"].append(f"R --quiet --vanilla -e '{custom_command_trelliscopejs}'")
    expected["packages"]["r"] = {"h2o": h2o, "trelliscopejs": trelliscopejs}
    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == expected["logs"][-1]

    actual_install_r = (env_io.env_dir / "install.R").read_text()
    expected_install_r = "\n".join([custom_command_h2o, custom_command_trelliscopejs])
    assert actual_install_r == expected_install_r


@pytest.mark.parametrize("quote_mark", ["'", r"\'"])
def test_r_install_single_quotes(setup_env, quote_mark, mocker):
    double_quote_command = 'install.packages("h2o")'
    expected_command = double_quote_command.replace('"', r"\'")
    command = double_quote_command.replace('"', quote_mark)
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])

    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False, "return_value.stderr": ""})
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        mocker.Mock(return_value={"h2o": "3.24.0.3"}),
    )
    h2o = Package("h2o", command)
    packages = Packages([h2o])

    RHandler(env=env).install(packages=packages)
    expected["logs"].append(f"R --quiet --vanilla -e $'{expected_command}'")
    expected["packages"]["r"] = {"h2o": h2o}
    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == expected["logs"][-1]

    actual_install_r = (env_io.env_dir / "install.R").read_text()
    assert actual_install_r == command


def test_remove_r_package(setup_env, mocker):
    env = setup_env["env"]
    env_io = setup_env["env_io"]
    expected = copy.deepcopy(setup_env["expected"])

    r_command = 'install.packages("h2o")'
    run_mock = mocker.patch("conda_env_tracker.gateways.r.run_command")
    run_mock.configure_mock(**{"return_value.failed": False, "return_value.stderr": ""})
    mocker.patch(
        "conda_env_tracker.env.get_r_dependencies",
        mocker.Mock(return_value={"h2o": Package("h2o", "h2o", "3.24.0.3")}),
    )

    handler = RHandler(env=env)
    h2o = Package("h2o", r_command)
    packages = Packages([h2o])
    handler.install(packages=packages)

    install_log = f"R --quiet --vanilla -e '{r_command}'"

    expected["logs"].append(install_log)
    expected["packages"]["r"] = {"h2o": h2o}

    actual = env_io.get_history()

    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == install_log

    expected_install_r = r_command
    actual_install_r = (env_io.env_dir / "install.R").read_text()
    assert actual_install_r == expected_install_r

    mocker.patch("conda_env_tracker.r.r_remove")
    handler.remove(packages=packages)
    actual = env_io.get_history()
    command = 'remove.packages(c("h2o"))'

    expected["packages"].pop("r")
    expected["logs"].append(f"R --quiet --vanilla -e '{command}'")
    assert actual.logs == expected["logs"]
    assert actual.packages == expected["packages"]
    assert actual.actions[-1] == expected["logs"][-1]

    assert not (env_io.env_dir / "install.R").exists()
