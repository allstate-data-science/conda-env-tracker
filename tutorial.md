# Conda-env-tracker Tutorial

## Install and Initialize conda-env-tracker

conda-env-tracker is currently only installable as a developer tool. Clone the repo and run `pip install conda-env-tracker/` on the repo directory.

Initialize conda-env-tracker with Auto: `(base) [user:~]$ cet init --auto`

## Onboarding New Team Member

We assume that the team member has already set up conda-env-tracker and is using conda-env-tracker auto.

```
(base) [user:~]$ git clone git@github.com:allstate-data-science/example-conda-env-tracker.git

Navigate to repo: `cd example-conda-env-tracker`
conda-env-tracker sync changes to 'cet-example' environment ([y]/n/stop asking)? y
...
Activate the 'cet-example' environment ([y]/n/stop asking)? y
(cet-example) [user:cet-example]$
```

## Creating a New conda-env-tracker Environment

conda-env-tracker auto uses information about the git repository in your current directory (see below if you don't want to use git). You should already have a git repo initialized or cloned and you should be in the corresponding directory when you call conda-env-tracker create.

```
(base) [user:~]$ git clone git@github.com:MyTeam/name-of-repo.git
(base) [user:~]$ cd name-of-repo
(base) [user:name-of-repo]$ cet create --sync --name name-of-env python=3.7 pandas
...
Activate the 'name-of-env' environment ([y]/n/stop asking)? y
(name-of-env) [user:name-of-repo]$
...
...
(name-of-env) [user:name-of-repo]$ git add .cet
(name-of-env) [user:name-of-repo]$ git commit ...
(name-of-env) [user:name-of-repo]$ git push ...
```

## Adding a Conda Library

```
(name-of-env) [user:name-of-repo]$ cet install jupyterlab pytest=4.6
(name-of-env) [user:name-of-repo]$ git add .cet
(name-of-env) [user:name-of-repo]$ git commit ...
(name-of-env) [user:name-of-repo]$ git push ...
```

## Adding a Pip Library

We recommend using packages from conda as much as possible. You should only use pip when your package is not available through conda.

```
(name-of-env) [user:name-of-repo]$ cet pip install pytest-pylint
(name-of-env) [user:name-of-repo]$ git add .cet
(name-of-env) [user:name-of-repo]$ git commit ...
(name-of-env) [user:name-of-repo]$ git push ...
```

## Adding an R Library

We recommend using the R packages from conda as much as possible, but some packages are not available in a conda channel

```
(name-of-env) [user:name-of-repo]$ cet r install trelliscopejs --command 'install.packages("treslliscopejs")'
(name-of-env) [user:name-of-repo]$ git add .cet
(name-of-env) [user:name-of-repo]$ git commit ...
(name-of-env) [user:name-of-repo]$ git push ...
```

## Pull Request

When installing a package on a development branch the files conda-env-tracker files will be part of the pull request. When the pull request is merged into the master branch the conda-env-tracker files will now include the additional packages from your pull request. When your teammate updates their repo, conda-env-tracker auto will recognize the local environment is out of sync with the conda-env-tracker environment described in the repository and update the local environment appropriately.

```
My Workflow:
Add Conda Library -> Create Pull Request -> Merge into Master

Teammate Workflow:
(name-of-env) [user:name-of-repo]$ git pull
conda-env-tracker sync changes to 'name-of-env' environment ([y]/n/stop asking)? y
...
(name-of-env) [user:name-of-repo]$
```

## Advanced Features

#### Channels

You can specify the conda channels in the `cet create` command and they will persist for all future installs using conda-env-tracker. If you do not give channels then they will be taken from your `.condarc` file.

#### Setting Up conda-env-tracker Without a Git Repo

You can create a conda-env-tracker environment without a git repo using the following commands in the project directory where you want to setup conda-env-tracker (if your are in a different directory then use the full path with `cet remote`).

```
(base) [user:project-dir]$ cet create --name name-of-env python=3.7 pandas
(base) [user:project-dir]$ cet remote --name name-of-env ./.cet
(base) [user:project-dir]$ cet sync --name name-of-env
```

#### Environment Rebuild

From time to time the best path forward with a broken conda environment is to rebuild it from scratch. We have included a conda-env-tracker rebuild command that will automate this process for you.

```
(name-of-env) [user:name-of-repo]$ conda deactivate
(base) [user:name-of-repo]$ cet rebuild -n name-of-env
(base) [user:name-of-repo]$ conda activate name-of-env
(name-of-env) [user:name-of-repo]$
```

#### Advanced conda-env-tracker Auto

By default `cet auto` asks each time you want change conda environments or sync changes to your conda-env-tracker environment.

There are two flags for more automation with `cet auto`:
 
* Use the `--activate` flag to active your conda environment without asking.
* Use the `--sync` flag to automatically sync changes to your conda-env-tracker environment without asking. This option is primarily for Jenkins or other automated build systems.
