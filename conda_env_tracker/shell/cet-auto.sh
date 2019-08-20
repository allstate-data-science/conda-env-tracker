#!/bin/bash


# Function that runs with every command prompt change
#
# Tests for multiple conditions to be met before asking user to update or activate a CET environment:
# 1. Is the CET_AUTO environment variable boolean True?
# 2. Is the cet command line tool found in the PATH?
# 3. Can the current working directory be connected to a .cet directory?
#
# If all 3 are true, then this directory uses cet and we do two final checks:
# * Does the remote history.yaml have more characters than the user home directory history.yaml?
#   If yes, then prompt the user to update (push/pull) the cet environment.
# * Does the current conda environment match the cet environment name?
#   If not, then prompt the user to activate the conda environment.
function cet_auto() {
    if [ $CET_AUTO ] && [ -x "$(command -v cet)" ]; then
        _set_cet_remote_dir
        if [[ $CET_REMOTE_DIR ]]; then
            _remote_history_file_time_changed "$CET_REMOTE_DIR"
            local HISTORY_REMOTE_FILE_TIME_CHANGED=$?
            if [ "$CET_REMOTE_DIR" != "$PREVIOUS_CET_REMOTE_DIR" ] || [ $HISTORY_REMOTE_FILE_TIME_CHANGED = 0 ]; then
                _ask_to_sync "$CET_REMOTE_DIR"
                _ask_to_activate "$CET_REMOTE_DIR"
            fi
        fi
        if [[ "$CET_REMOTE_DIR" != "$PREVIOUS_CET_REMOTE_DIR" ]]; then
            export PREVIOUS_CET_REMOTE_DIR="$CET_REMOTE_DIR"
        fi
    fi
}

# Search for a .cet/ directory in current working directory with a history.yaml file.
# Failing that, try to see if we are in a git repo and find a .cet/ directory in the
#   root directory with a history.yaml file.
# If both checks fail then set cet remote dir to an empty string.
function _set_cet_remote_dir() {
    export CET_REMOTE_DIR="$PWD/.cet"
    if [[ $CET_REMOTE_DIR ]]; then
        if [ -f "$CET_REMOTE_DIR/history.yaml" ]; then
            return 0
        fi
    fi
    local GIT_ROOT_DIR=`git rev-parse --show-toplevel 2> /dev/null;`
    if [[ $GIT_ROOT_DIR ]]; then
        export CET_REMOTE_DIR="$GIT_ROOT_DIR/.cet"
        if [ -f "$CET_REMOTE_DIR/history.yaml" ]; then
            return 0
        fi
    fi
    export CET_REMOTE_DIR=""
    return 1
}

# Check if remote history file has more characters than local history file.
# If so then run sync.
function _ask_to_sync() {
    local CET_REMOTE_DIR="$1"
    local CET_ENV_NAME=$(_get_cet_env_name "$CET_REMOTE_DIR")
    local CET_LOCAL_DIR="$HOME/.cet/envs/$CET_ENV_NAME"
    local CET_REMOTE_HISTORY_CHAR_COUNT=`cat "$CET_REMOTE_DIR/history.yaml" | wc -m`
    if [ -f "$CET_LOCAL_DIR/history.yaml" ]; then
        local CET_LOCAL_HISTORY_CHAR_COUNT=`cat "$CET_LOCAL_DIR/history.yaml" | wc -m`
    else
        local CET_LOCAL_HISTORY_CHAR_COUNT=0
    fi
    if (( $CET_REMOTE_HISTORY_CHAR_COUNT > $CET_LOCAL_HISTORY_CHAR_COUNT )) ; then
        if [ $CET_SYNC_AUTO ]; then
            eval "cet remote --name $CET_ENV_NAME $CET_REMOTE_DIR --if-missing && cet sync --infer"
        else
            >&2 _ask_to_run "Conda-env-tracker sync changes to '$CET_ENV_NAME' environment" "cet remote --name $CET_ENV_NAME $CET_REMOTE_DIR --if-missing && cet sync --infer"
        fi
    fi
}

# Check if current conda environment is equal to cet environment.
# If not, then ask to activate cet conda environment.
function _ask_to_activate() {
    local CET_ENV_NAME=$(_get_cet_env_name "$1")
    if [ $CET_AUTO ] && [ "$CONDA_DEFAULT_ENV" != "$CET_ENV_NAME" ]; then
        if [ $CONDA_EXE ]; then
            local CONDA_BIN_DIR=`dirname $CONDA_EXE`
        else
            local WHICH_CONDA=`which conda`
            local CONDA_BIN_DIR=`dirname $WHICH_CONDA`
        fi
        local CONDA_FUNCTIONS_SCRIPT="$CONDA_BIN_DIR/../etc/profile.d/conda.sh"
        . "$CONDA_FUNCTIONS_SCRIPT"
        if [ $CET_ACTIVATE_AUTO ]; then
            eval "conda activate $CET_ENV_NAME"
        else
            _ask_to_run "Activate the '$CET_ENV_NAME' environment" "conda activate $CET_ENV_NAME"
        fi
    fi
}

function _get_cet_env_name() {
    local CET_REMOTE_DIR="$1"
    local CET_ENV_NAME=`head -n 1 "$CET_REMOTE_DIR/history.yaml" | awk -F ": " '{print $2}'`
    echo "$CET_ENV_NAME"
}

function _remote_history_file_time_changed() {
    local CET_REMOTE_DIR="$1"
    if uname | grep -q "Darwin"; then
        mod_time_fmt="-f %m"
    else
        mod_time_fmt="-c %Y"
    fi
    if [ -f "$1/history.yaml" ]; then
        local NEW_HISTORY_FILE_TIME=`stat $mod_time_fmt "$CET_REMOTE_DIR"/history.yaml`
    fi
    local current_file_time="CET_HISTORY_FILE_TIME_REMOTE"
    local CET_HISTORY_FILE_TIME="${!current_file_time}"
    if [ "$NEW_HISTORY_FILE_TIME" != "$CET_HISTORY_FILE_TIME" ]; then
        export CET_HISTORY_FILE_TIME_REMOTE=$NEW_HISTORY_FILE_TIME
        return 0
    fi
    return 1
}

# Prompt the user to execute the relevant command or snooze cet auto for this prompt session.
function _ask_to_run() {
    while true; do
        read -p "$1 ([y]/n/stop asking)? " answer
        local lower=`echo "$answer" | awk '{print tolower($0)}'`
        unset answer
        case ${lower} in
            y|yes|"" )
                eval "$2"; break;
            ;;
            n|no )
                break;
            ;;
            s|stop )
                (>&2 echo "Stopping for current session. run 'export CET_AUTO=0' to resume."); unset CET_AUTO; break;
            ;;
            * )
                echo "Please answer 'yes', 'no', or 'stop'."
            ;;
        esac
    done
}

export CET_AUTO=0
export PROMPT_COMMAND=cet_auto
