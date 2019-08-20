# conda-env-tracker
conda-env-tracker makes it simple to keep your software environment up to date. Manage python, R, and conda packages (of any language) for multiple projects with ease.

## Requirements

* python >= 3.6
* Anaconda/Miniconda install
* conda >= 4.5

If you are using an old version of conda we recommend updating:

```
$ conda update -n base conda
$ conda init
```

## Install

Currently you can only install directly from GitHub by cloning and running `pip install conda-env-tracker/`. We recommend installing in your base conda environment.

## Getting Started

1. Initialize the conda-env-tracker command line tool. Only needs to be done once, right after installing. Using `--auto` runs `cet auto` which will automatically check if you need to be synced with the conda-env-tracker environment in your current git repo.

`$ cet init --auto`

2. Clone or navigate to a git repo:

```
$ git clone git@github.com:Name/my-repo.git # If necessary
$ cd my-repo
conda-env-tracker sync changes to 'my-env' environment ([y]/n/stop asking)? y
...
Activate the 'my-env' environment ([y]/n/stop asking)? y
(my-env) $
```

If there is a conda-env-tracker environment in the repo, then you will be asked to sync the environment and activate it. Otherwise learn how to create an environment in the next section.

#### Create a new environment

Create a new environment from inside a git repo:

```
$ cet create --sync --name my-env python=3.7 pandas
...
Activate the 'my-env' environment ([y]/n/stop asking)?
```

sync and commit the changes:

```
$ git add .cet/*
$ git commit -m "Add cet"
```

#### Installing Packages

Activate an environment (`conda activate my-env` if necessary) and run

`(my-env) $ cet install jupyter`

or (only recommended for packages not available via conda)

`(my-env) $ cet pip install arcgis`

or (similarly, only recommended for packages not available via conda)

`(my-env) $ cet r install testthat --command 'install.packages("testthat")'`

If you are in the git repo associated with this environment conda-env-tracker will automatically suggest a sync, but you can force one using

`(my-env) $ cet sync`
