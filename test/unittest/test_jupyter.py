"""Test jupyter related functions"""

import subprocess

import pytest

from conda_env_tracker.gateways.jupyter import jupyter_kernel_install_query
from conda_env_tracker.packages import Package


@pytest.mark.parametrize(
    "packages",
    [
        [Package.from_spec("pandas"), Package.from_spec("jupyter")],
        [Package.from_spec("jupyterlab"), Package.from_spec("numpy")],
    ],
)
def test_jupyter_kernel_install_query_success(mocker, packages):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")
    run_mock.configure_mock(
        **{
            "return_value.returncode": 0,
            "return_value.stdout": (
                "Available kernels:\n"
                "  arl             /home/username/.local/share/jupyter/kernels/arl\n"
                "  test-env        /home/username/.local/share/jupyter/kernels/test-env\n"
                "  rasterstats     /home/username/.local/share/jupyter/kernels/rasterstats"
            ),
        }
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.prompt_yes_no",
        new=mocker.Mock(return_value=True),
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.is_current_conda_env",
        new=mocker.Mock(return_value=True),
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")

    jupyter_kernel_install_query(name="myenv", packages=packages)

    debug_mock.assert_not_called()
    assert run_mock.call_args_list == [
        mocker.call(
            "jupyter kernelspec list",
            shell=True,
            stdout=subprocess.PIPE,
            encoding="UTF-8",
        ),
        mocker.call(
            "python -m ipykernel install --name myenv --user",
            shell=True,
            stderr=subprocess.PIPE,
            encoding="UTF-8",
        ),
    ]
    run_mock.assert_called_with(
        "python -m ipykernel install --name myenv --user",
        shell=True,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )


def test_jupyter_kernel_install_query_success_from_different_env(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")
    run_mock.configure_mock(
        **{
            "return_value.returncode": 0,
            "return_value.stdout": (
                "Available kernels:\n"
                "  arl             /home/username/.local/share/jupyter/kernels/arl\n"
                "  test-env        /home/username/.local/share/jupyter/kernels/test-env\n"
                "  rasterstats     /home/username/.local/share/jupyter/kernels/rasterstats"
            ),
        }
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.prompt_yes_no",
        new=mocker.Mock(return_value=True),
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.is_current_conda_env",
        new=mocker.Mock(return_value=False),
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.get_conda_activate_command",
        new=mocker.Mock(return_value="conda activate myenv"),
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")

    jupyter_kernel_install_query(name="myenv", packages=[Package.from_spec("jupyter")])

    debug_mock.assert_not_called()
    assert run_mock.call_args_list == [
        mocker.call(
            "conda activate myenv && jupyter kernelspec list",
            shell=True,
            stdout=subprocess.PIPE,
            encoding="UTF-8",
        ),
        mocker.call(
            "conda activate myenv && python -m ipykernel install --name myenv --user",
            shell=True,
            stderr=subprocess.PIPE,
            encoding="UTF-8",
        ),
    ]


def test_jupyter_kernel_install_query_kernel_exists(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")
    run_mock.configure_mock(
        **{
            "return_value.returncode": 0,
            "return_value.stdout": (
                "Available kernels:\n"
                "  arl             /home/username/.local/share/jupyter/kernels/arl\n"
                "  test-env        /home/username/.local/share/jupyter/kernels/test-env\n"
                "  rasterstats     /home/username/.local/share/jupyter/kernels/rasterstats"
            ),
        }
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")

    jupyter_kernel_install_query(
        name="rasterstats", packages=[Package.from_spec("jupyter")]
    )

    debug_mock.assert_called_once_with(
        "rasterstats is already installed as a jupyter kernel"
    )
    assert len(run_mock.call_args_list) == 1


def test_jupyter_kernel_install_query_user_says_no(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")
    run_mock.configure_mock(
        **{
            "return_value.returncode": 0,
            "return_value.stdout": (
                "Available kernels:\n"
                "  arl             /home/username/.local/share/jupyter/kernels/arl\n"
                "  test-env        /home/username/.local/share/jupyter/kernels/test-env\n"
                "  rasterstats     /home/username/.local/share/jupyter/kernels/rasterstats"
            ),
        }
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.prompt_yes_no",
        new=mocker.Mock(return_value=False),
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")

    jupyter_kernel_install_query(name="myenv", packages=[Package.from_spec("jupyter")])

    debug_mock.assert_not_called()
    assert len(run_mock.call_args_list) == 1


def test_jupyter_kernel_install_query_jupyter_not_in_packages(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")

    jupyter_kernel_install_query(name="myenv", packages=[Package.from_spec("numpy")])

    run_mock.assert_not_called()


def test_jupyter_kernel_install_query_jupyter_cant_get_kernelspec(mocker):
    run_mock = mocker.patch("conda_env_tracker.gateways.jupyter.subprocess.run")
    run_mock.configure_mock(
        **{"return_value.returncode": 1, "return_value.stderr": "err"}
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")

    jupyter_kernel_install_query(name="myenv", packages=[Package.from_spec("jupyter")])

    debug_mock.assert_called_once_with("Error while installing jupyter kernel: err")
    assert len(run_mock.call_args_list) == 1


def test_jupyter_kernel_install_query_jupyter_cant_install_kernel(mocker):
    run_mock = mocker.patch(
        "conda_env_tracker.gateways.jupyter.subprocess.run",
        new=mocker.Mock(
            side_effect=[
                mocker.Mock(
                    returncode=0,
                    stdout=(
                        "Available kernels:\n"
                        "  arl             /home/username/.local/share/jupyter/kernels/arl\n"
                        "  test-env        /home/username/.local/share/jupyter/kernels/test-env\n"
                        "  rasterstats     /home/username/.local/share/jupyter/kernels/rasterstats"
                    ),
                ),
                mocker.Mock(returncode=1, stderr="another err"),
            ]
        ),
    )
    debug_mock = mocker.patch("conda_env_tracker.gateways.jupyter.logger.debug")
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.prompt_yes_no",
        new=mocker.Mock(return_value=True),
    )
    mocker.patch(
        "conda_env_tracker.gateways.jupyter.is_current_conda_env",
        new=mocker.Mock(return_value=True),
    )

    jupyter_kernel_install_query(name="myenv", packages=[Package.from_spec("jupyter")])

    debug_mock.assert_called_once_with(
        "Error while installing jupyter kernel: another err"
    )
    run_mock.assert_called_with(
        "python -m ipykernel install --name myenv --user",
        shell=True,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )
    assert len(run_mock.call_args_list) == 2
