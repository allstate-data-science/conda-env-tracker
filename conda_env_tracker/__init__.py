"""conda_env_tracker is a package to help teams manage and share conda environments.

conda_env_tracker separates packages (the software we want) and dependencies (the stuff that comes along with it).

Example
 `conda create --name test python=3.6 pandas`
  has two packages: python, pandas
  and lots of dependencies: setuptools, numpy, etc.
"""
import logging

from conda_env_tracker.main import create, conda_install

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Conda-env-tracker: %(message)s",
    datefmt="%m-%d %H:%M",
)
