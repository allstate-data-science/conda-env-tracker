"""Create useful universal types."""

from pathlib import Path
from typing import List, Tuple, Union

ListLike = Union[List[str], Tuple[str, ...]]
PathLike = Union[Path, str]
