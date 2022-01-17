import re
import inspect
from typing import Optional
from .cache import Cache
from .datetime import Datetime
from .request import Request
from .database import Database
from .check import Check
from .format import Format

__all__ = ['Breathecode']


def print_arguments(func: callable) -> str:
    try:
        varnames = str(inspect.signature(func))
    except ValueError:
        raise Exception(f'{func.__name__} is a invalid function/method')

    return varnames.replace('self, ', '').replace('cls, ', '')


class Breathecode:
    """Collection of wrappers of last implementation mixin for testing purposes"""

    cache: Cache
    datetime: Datetime
    request: Request
    database: Database
    check: Check
    format: Format

    def __init__(self, parent) -> None:
        self.parent = parent

        self.cache = Cache(parent)
        self.datetime = Datetime(parent)
        self.request = Request(parent)
        self.database = Database(parent)
        self.check = Check(parent)
        self.format = Format(parent)

    def help(self, level: int = 0, parent: Optional[dict] = None, last_item: bool = False) -> list[str]:
        """Print a list of mixin with a tree style (command of Linux)"""

        result: list[str] = []

        if not parent:
            result.append('bc')

        parent = [x for x in dir(parent or self) if not x.startswith('_')]

        if last_item:
            starts = '    ' + ('│   ' * (level - 1))

        else:
            starts = '│   ' * level

        for key in parent:
            item = getattr(self, key)

            if callable(item):
                result.append(f'{starts}├── {key}{print_arguments(item)}')

            else:
                result.append(f'{starts}├── {key}')

                last_item = parent.index(key) == len(parent) - 1
                result = [*result, *Breathecode.help(item, level + 1, item, last_item)]

        result[-1] = result[-1].replace('  ├── ', '  └── ')
        result[-1] = result[-1].replace(r'├── ([a-zA-Z0-9]+)$', r'└── \1')

        for n in range(len(result) - 1, -1, -1):
            if result[n][0] == '├':
                result[n] = re.sub(r'^├', r'└', result[n])
                break

        if level == 0:
            print('\n'.join(result))

        return result
