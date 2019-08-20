#!/usr/bin/env python3

import os
import pathlib
import shutil
import sys

import click
import pytest

PACKAGE_DIR = "conda_env_tracker"


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="Run all tests including end-to-end tests",
)
@click.option("-v", "verbose", flag_value="-v", default=False)
@click.option("-vv", "verbose", flag_value="-vv", default=False)
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def run_tests(all, verbose, pytest_args):
    """Run automated tests. By default, only run unit tests."""
    returncode = _run_tests(all=all, verbose=verbose, pytest_args=pytest_args)
    sys.exit(returncode)


def _run_tests(all, verbose, pytest_args):
    _remove_pycache(PACKAGE_DIR)
    args = ["--pylint", "--cov-report", "term-missing", f"--cov={PACKAGE_DIR}"]
    if verbose:
        args.append(verbose)
    if pytest_args:
        args.extend(pytest_args)
    if not [arg for arg in args if arg == "-x" or arg.startswith("--maxfail")]:
        args.append("--maxfail=10")
    if all:
        args.append("-s")
        if not verbose:
            args.append("-vv")
    else:
        path = pathlib.Path(__file__).parent / "test" / "integrationtest"
        args.append(f"--ignore={path}")
    return pytest.main(args)


def _remove_pycache(dir):
    """Remove pycache directories."""
    pycache = os.path.join(dir, "__pycache__")
    shutil.rmtree(pycache, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
