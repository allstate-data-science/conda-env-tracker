# Conda-env-tracker Docs

## Getting Started

To get started consult the Getting Started (see README) guide for installing and configuring cet.

#### Installing

We recommend installing by cloning and pip installing conda-env-tracker in your base environment.

## Commandline

Below is full list of commands with specific description of certain flags.

#### Initialization (REQUIRED)

conda-env-tracker must be initialized after installation. This command only needs to be run one time after installation. Generally you will not need to reinitialize if you update to a newer version of conda-env-tracker.

We recommend setting up conda-env-tracker with the `--auto` option.

* `cet init --auto` or `cet auto` will setup the automatic conda environment activation and syncing with git repos.

You can also initialize conda-env-tracker without using auto.

* `cet init` will make the conda-env-tracker command line tool available from every conda environment.


#### Environments

We recommend running these commands from your associated github repo.

conda-env-tracker will include the channels from your conda create command to define the channels associated with your conda-env-tracker environment. If you do not specify any channels, they will be taken from your `.condarc`.

* `cet create --sync` will push the created environment into the root directory of the git repo in the current working directory.

* `cet create` or `cet conda create` creates a conda environment.

* `cet create --infer` will create the conda-env-tracker `history.yaml` and `conda-env.yaml` from an existing conda environment.

* `cet remove` will remove a the conda environment and all conda-env-tracker files.

* `cet rebuild` will rebuild the conda environment from the conda-env-tracker files.

#### Managing Packages

###### Conda Packages

* `cet conda install` installs conda packages.

* `cet conda remove` removes conda packages.

* `cet conda update --all` updates all packages. Note that one can add a specific version to this command, e.g. `cet conda update python=3.7 --all`.

###### Pip Packages

* `cet pip install` installs packages from [pypi](https://pypi.org/) using [pip](https://pip.pypa.io/en/latest/).

* `cet pip install <package> --custom <package_url>` installs a pip package from a custom url.

###### R Packages

* `cet r install <package> --command <r_command>` installs an R package from an R command.

    For example, `cet r install h2o --command 'install.packages("h2o")'` will install h2o.

#### Remote Git Repository

If you are using conda-env-tracker auto you are unlikely to use any of these commands.

* `cet remote` will specify the remote directory for the conda-env-tracker environment. Default behavior is to put it in the `.cet/` folder of the root directory of the current git repo, but user can supply a remote directory path to override this behavior.

* `cet sync` will check if the conda-env-tracker environment needs to pull changes from remote into local (and update the conda environment) or push changes from local into the remote. Can also use `cet pull` and `cet push` to separate these commands.

#### History

* `cet history update` will allow the user to update the history to add or remove packages that were installed/removed without using conda-env-tracker, e.g. `cet history update pandas` will add pandas to the history.

* `cet history update --channel` will append a channel to the list of channels in the conda-env-tracker files.

## Conda-env-tracker Auto

conda-env-tracker auto simplifies the use of conda-env-tracker by automating most of the manual bookkeeping required to maintain files describing your environment. While conda-env-tracker auto will sync environment changes to the local copy of your github repo, you must added the modified files to your git commit in order to share with your teammates.

* conda-env-tracker auto automatically switches conda environments when you change to a new conda-env-tracker directory.
* conda-env-tracker auto automatically syncs environment metadata file updates to the `.cet` directory of your github repo.
* conda-env-tracker auto recognizes when the environment metadata files from your repo are out of sync with your local environment and updates appropriately.

To setup conda-env-tracker auto:

* `cet init --auto`

* `cet auto` if conda-env-tracker has already been initialized.

#### Advanced conda-env-tracker Auto

There are two flags for more automation with `cet auto`:
 
* Use the `--activate` flag to active your conda environment without asking.
* Use the `--sync` flag to automatically sync changes to your conda-env-tracker environment without asking. This option is primarily for Jenkins or other automated build systems.

## Motivation

To understand the motivation see: [pipenv](https://pipenv.readthedocs.io/en/latest/basics/) vs [conda env export](https://conda.io/docs/user-guide/tasks/manage-environments.html#exporting-the-environment-file). We want it to be easy to keep track of the packages that matter (e.g. `pandas`, `pytest`) and ignore the dependencies that come along for the ride (e.g. `libstdcxx-ng`). We also want to track how the package got to this point so that it is reproducible.

## How It All Works

#### Files

conda-env-tracker tracks the environment using different files. These files are stored locally (in `~/.cet/envs`) and in a remote directory (typically in the `.cet/` folder of the root directory of a git repo).

* `history.yaml`: tracks the user commands used to create and install packages into the environment. It has 6 sections:
    * `name`: the name of the conda environment.
    * `channels`: the list of conda channels used to create the environment. The channel list is kept consistent for subsequent install commands.
    * `packages`: list of packages installed by the user. There are three potential subsections:
        * `conda`: conda packages.
        * `pip`: pip packages.
        * `r`: R packages.
    * `logs`: the install commands as given by the user.
    * `actions`: a fully reproducible install command with all required information (e.g. version, date, build string, channel, etc.).
    * `debug`: debug information for the install command including platform, conda version, pip version and a timestamp.

* `conda-env.yaml`: the channels and user specified packages with versions. This file is compatible across platforms (unless a package is only available on one platform).
* `install.R`: the R packages with versions and dates specified.