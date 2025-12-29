"""Storage backends for benchmark results"""

from .sqlite import SQLiteStorage
from .json import JsonStorage

__all__ = ["SQLiteStorage", "JsonStorage"]
