"""Conda-env-tracker is a package to help teams manage and share conda environments.

Conda-env-tracker separates packages (the software we want) and dependencies (the stuff that comes along with it).

Example
 `conda create --name test python=3.6 pandas`
  has two packages: python, pandas
  and lots of dependencies: setuptools, numpy, etc.
"""
import logging
from pkg_resources import get_distribution, DistributionNotFound

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Conda-env-tracker: %(message)s",
    datefmt="%m-%d %H:%M",
)


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    __version__ = None
