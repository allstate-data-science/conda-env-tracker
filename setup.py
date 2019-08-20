#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="conda_env_tracker",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="Track changes to a conda environment and automatically keep you and collaborators up-to-date.",
    author="Jesse Lord",
    author_email="jessewlord@gmail.com",
    url="github.com/allstate-data-science/conda-env-tracker",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["click", "colorama", "oyaml>=0.8", "pyyaml>=5.0", "invoke"],
    tests_require=[
        "pytest",
        "pytest-mock",
        "pytest-cov",
        "pylint",
        "pytest-pylint",
        "hypothesis",
    ],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["cet=conda_env_tracker.cmdline:cli"]},
)
