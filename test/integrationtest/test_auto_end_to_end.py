"""Testing the conda_env_tracker auto shell function which creates a PROMPT_COMMAND to run after every command in a terminal.

When useful the shell function prompts the user to:
  1. push/pull latest changes between local conda_env_tracker and remote conda_env_tracker directory
  2. source activate the relevant conda environment

The conda_env_tracker auto shell function makes several tests to prevent unnecessarily bothering the user.
The checks:
  1. Environment variable CET_AUTO is not null
  2. The current directory has a cet remote directory
  3. The cet remote directory has a history.yaml file.
  4. Either
    A. The cet remote directory is different from environment variable PREVIOUS_CET_DIR (which is updated by
       the function)
    B. The modify time on the cet_remote_dir/history.yaml has changed since previous check.

Then if:
  - The remote history file has more characters than the local history file, then it asks to push/pull.
  - The environment variable CONDA_DEFAULT_ENV differs from environment name in remote history.yaml, then it asks
    to source activate the environment from the remote history.yaml.
"""

# pylint: disable=redefined-outer-name

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from conda_env_tracker import errors, main
from conda_env_tracker.gateways import conda
from conda_env_tracker.gateways.io import USER_ENVS_DIR

if not os.environ["SHELL"].endswith("bash"):
    pytest.skip("Can only test with bash", allow_module_level=True)

SHELL_AUTO_FILE = Path(main.__file__).parent / "shell" / "cet-auto.sh"
CET_ENV_NAME = "cet_auto_end_to_end_test"
BASE_ENV_NAME = "base"
UNSEEN_ENV_NAME = "unseen-cet-env"


@pytest.fixture(scope="module", params=[True, False])
def setup_env(request):
    """Creating cet remotes to test cet auto shell script."""
    # pylint: disable=too-many-statements
    env_dir = USER_ENVS_DIR / CET_ENV_NAME
    unseen_local_dir = USER_ENVS_DIR / UNSEEN_ENV_NAME

    empty_dir = Path.home() / ".cet" / "empty_dir"
    cet_dir = Path.home() / ".cet" / "cet_dir"
    identical_history_dir = Path.home() / ".cet" / "identical_history_dir"
    unseen_cet_dir = Path.home() / ".cet" / "unseen_cet_dir"

    remote_path = cet_dir / ".cet"
    identical_remote_path = identical_history_dir / ".cet"
    unseen_remote = unseen_cet_dir / ".cet"

    def teardown():
        conda.delete_conda_environment(name=CET_ENV_NAME)
        conda.delete_conda_environment(name=UNSEEN_ENV_NAME)
        if env_dir.is_dir():
            shutil.rmtree(env_dir)
        if cet_dir.is_dir():
            shutil.rmtree(cet_dir)
        if unseen_cet_dir.is_dir():
            shutil.rmtree(unseen_cet_dir)
        if identical_history_dir.is_dir():
            shutil.rmtree(identical_history_dir)
        if empty_dir.is_dir():
            shutil.rmtree(empty_dir)
        if unseen_local_dir.is_dir():
            shutil.rmtree(unseen_local_dir)

    request.addfinalizer(teardown)

    empty_dir.mkdir()
    cet_dir.mkdir()
    identical_history_dir.mkdir()
    unseen_cet_dir.mkdir()

    if request.param:
        subprocess.run(f"cd {empty_dir}; git init --quiet", shell=True)
        subprocess.run(f"cd {cet_dir}; git init --quiet", shell=True)
        subprocess.run(f"cd {identical_history_dir}; git init --quiet", shell=True)
        subprocess.run(f"cd {unseen_cet_dir}; git init --quiet", shell=True)

    remote_path.mkdir()
    identical_remote_path.mkdir()
    unseen_remote.mkdir()

    try:
        env = main.create(
            name=CET_ENV_NAME, specs=["python"], channels=["defaults"], yes=True
        )
        main.setup_remote(name=CET_ENV_NAME, remote_dir=remote_path, yes=True)
        main.push(name=env.name)
    except errors.CondaEnvTrackerCondaError as err:
        teardown()
        raise err

    remote_history_file = remote_path / "history.yaml"
    content = remote_history_file.read_text()

    # We add newline characters to the remote history file so that the unix utility `wc -m` will find more
    # characters in the remote history.yaml file than in the local history.yaml file. This prompts the cet_auto
    # shell function to ask the user to pull the changes from remote into local.
    additional_characters = "\n\n\n"
    remote_history_file.write_text(content + additional_characters)

    identical_remote_history_file = identical_remote_path / "history.yaml"
    identical_remote_history_file.write_text(content)

    unseen_history_file = unseen_remote / "history.yaml"
    unseen_history_file.write_text(content.replace(CET_ENV_NAME, UNSEEN_ENV_NAME))

    local_conda_env = env_dir / "environment.yml"
    conda_env_content = local_conda_env.read_text()
    unseen_conda_env = unseen_remote / "environment.yml"
    unseen_conda_env.write_text(
        conda_env_content.replace(CET_ENV_NAME, UNSEEN_ENV_NAME)
    )

    return {
        "cet": cet_dir,
        "empty_cet": empty_dir,
        "identical_cet": identical_history_dir,
        "unseen_cet": unseen_cet_dir,
        "remote_history_file": remote_history_file,
        "local_history_file": env_dir / "history.yaml",
    }


@pytest.mark.parametrize("input", ["\n\n", "\ny\ny\n", "yes\nyes\n", "\ny\n", "y\n\n"])
def test_cd_cet_yes_pushpull_yes_activate(setup_env, input):
    cet = setup_env["cet"]

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr)


def test_cd_cet_no_pushpull_no_activate(setup_env):
    cet = setup_env["cet"]
    input = "n\nn\n"

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_no_env_activated(stdout)
    _assert_no_pushpull(stderr)


@pytest.mark.parametrize("input", ["\nn\n", "y\nn\n", "yes\nno\n"])
def test_cd_cet_yes_pushpull_no_activate(setup_env, input):
    cet = setup_env["cet"]

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_no_env_activated(stdout)
    _assert_yes_pushpull(stderr)


@pytest.mark.parametrize("input", ["n\n\n", "n\ny\n", "no\nyes\n"])
def test_cd_cet_no_pushpull_yes_activate(setup_env, input):
    cet = setup_env["cet"]

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_yes_env_activated(stdout)
    _assert_no_pushpull(stderr)


@pytest.mark.parametrize("input", ["s\n", "n\ns\n"])
def test_cd_cet_stop_for_session(setup_env, input):
    cet = setup_env["cet"]
    empty_cet = setup_env["empty_cet"]

    stdout, stderr = _run_shell(
        f"cd {cet};cd {empty_cet};cd {cet};echo $CONDA_DEFAULT_ENV", input=input
    )
    _assert_no_env_activated(stdout)
    assert (
        stderr[0] == "Stopping for current session. run 'export CET_AUTO=0' to resume."
    )
    assert len(stderr) == 1


def test_cd_empty(setup_env):
    empty_cet = setup_env["empty_cet"]

    stdout, stderr = _run_shell(f"cd {empty_cet};echo $CONDA_DEFAULT_ENV")
    _assert_no_env_activated(stdout)
    _assert_no_pushpull(stderr)


def test_cd_cet_cd_subdir(setup_env):
    """Changing directories after entering the cet should not trigger a second pushpull."""
    cet = setup_env["cet"]

    stdout, stderr = _run_shell(
        f"cd {cet};cd .cet;echo $CONDA_DEFAULT_ENV", input="\n\n"
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr, num_pushpull=1)


def test_cd_cet_twice(setup_env):
    cet = setup_env["cet"]
    empty_cet = setup_env["empty_cet"]

    stdout, stderr = _run_shell(
        f"cd {cet};cd {empty_cet};cd {cet};echo $CONDA_DEFAULT_ENV", input="\nn\n\n\n"
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr, num_pushpull=2)


def test_cd_cet_edit_local_history_cd_subdir(setup_env):
    """Editing the local history file does nothing."""
    cet = setup_env["cet"]
    history_file = setup_env["local_history_file"]

    stdout, stderr = _run_shell(
        f'cd {cet};sleep 1;echo " " >> {history_file};cd .cet;echo $CONDA_DEFAULT_ENV',
        input="\n\n",
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr, num_pushpull=1)


def test_cd_cet_edit_remote_history_cd_subdir(setup_env):
    """Editing the remote history file triggers a new pushpull, even without changing from the cet dir."""
    cet = setup_env["cet"]
    history_file = setup_env["remote_history_file"]

    stdout, stderr = _run_shell(
        f'cd {cet};sleep 1;echo "\n\n\n" >> {history_file};cd .cet;echo $CONDA_DEFAULT_ENV',
        input="\nn\n\n\n",
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr, num_pushpull=2)


def test_cd_unseen_cet_no_sync_no_activate(setup_env):
    """Test a cet with a new cet that has never been seen in user cet environments."""
    cet = setup_env["unseen_cet"]
    input = "n\nn\n"

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_no_env_activated(stdout)
    _assert_no_pushpull(stderr)


def test_cd_unseen_cet_yes_sync_yes_activate(setup_env):
    """Test a cet with a new cet that has never been seen in user cet environments."""
    cet = setup_env["unseen_cet"]
    input = "y\ny\n"

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    assert stdout == UNSEEN_ENV_NAME
    assert any(
        "Conda-env-tracker: Successfully updated the environment." in line
        for line in stderr
    )


def test_cd_identical_cet_only_activate(setup_env):
    """Test a cet with exact same history.yaml content as local."""
    cet = setup_env["identical_cet"]
    input = "y\ny\n"

    stdout, stderr = _run_shell(f"cd {cet};echo $CONDA_DEFAULT_ENV", input=input)
    _assert_yes_env_activated(stdout)
    _assert_no_pushpull(stderr)


def test_conda_deactivate_base(setup_env):
    """Test that conda deactivate puts us in base env."""
    cet = setup_env["cet"]
    input = "\n\n"

    stdout, stderr = _run_shell(
        f"cd {cet};conda deactivate;echo $CONDA_DEFAULT_ENV", input=input
    )
    _assert_no_env_activated(stdout)
    _assert_yes_pushpull(stderr)


def test_conda_deactivate_cd_home_dir_cd_cet_again(setup_env):
    """Test that cding to home and then back after conda deactivate asks to re-activate again."""
    cet = setup_env["cet"]
    input = "\n\n\n\n"

    stdout, stderr = _run_shell(
        f"cd {cet};conda deactivate;cd $HOME;cd {cet};echo $CONDA_DEFAULT_ENV",
        input=input,
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr, num_pushpull=2)


@pytest.mark.parametrize("input", ["\n", "y\n", "yes\n"])
def test_activate_auto(setup_env, input):
    """Test that when CET_ACTIVATE_AUTO=0 that it does not ask to activate the environment."""
    cet = setup_env["cet"]

    stdout, stderr = _run_shell(
        f"cd {cet};echo $CONDA_DEFAULT_ENV",
        input=input,
        activate_auto="export CET_ACTIVATE_AUTO=0",
    )
    _assert_yes_env_activated(stdout)
    _assert_yes_pushpull(stderr)


def _assert_yes_env_activated(stdout):
    """New environment was activated."""
    assert stdout == CET_ENV_NAME


def _assert_no_env_activated(stdout):
    """New environment was not activated."""
    assert stdout == BASE_ENV_NAME


def _assert_yes_pushpull(stderr, num_pushpull=1):
    """Ran cet push/pull."""
    num_text_lines = 2
    assert len(stderr) == num_text_lines * num_pushpull
    for i in range(num_pushpull):
        assert "Conda-env-tracker: Nothing to pull." in stderr[i * num_text_lines]
        assert "Conda-env-tracker: Nothing to push." in stderr[i * num_text_lines + 1]


def _assert_no_pushpull(stderr):
    """Did not run cet push/pull."""
    assert not stderr[0]
    assert len(stderr) == 1


def _run_shell(
    command,
    input="",
    environment=BASE_ENV_NAME,
    activate_auto="unset CET_ACTIVATE_AUTO",
):
    shell_auto_file = str(SHELL_AUTO_FILE).replace(" ", r"\ ")
    activate = Path(os.environ["CONDA_EXE"]).parent / "activate"
    prefix = f"{activate_auto};source {shell_auto_file};trap cet_auto DEBUG;source {activate} {environment};"
    process = subprocess.run(
        prefix + command,
        shell=True,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="UTF-8",
    )
    stdout = process.stdout.strip()
    stderr = process.stderr.strip().split("\n")
    print(stdout)
    print(stderr)
    return stdout, stderr
