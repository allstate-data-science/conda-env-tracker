"""Utility functions"""

from conda_env_tracker.types import ListLike


def prompt_yes_no(prompt_msg: str) -> bool:
    """Ask user to overwrite the local with remote"""
    answer = input(prompt_msg + " ([y]/n)? ").lower()
    while answer not in ["yes", "y", "no", "n", ""]:
        answer = input(f'Found {answer}, expected "y" or "n".\n{prompt_msg}').lower()
    if answer in ["no", "n"]:
        return False
    return True


def is_ordered_subset(set: ListLike, subset: ListLike) -> bool:
    """Return true if all element in subset are in set and in order"""
    set_iterator = iter(set)
    return all(element in set_iterator for element in subset)
