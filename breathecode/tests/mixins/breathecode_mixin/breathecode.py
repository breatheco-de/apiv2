import re
import inspect
from rest_framework.test import APITestCase
from typing import Optional
from faker import Faker
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
    """Collection of mixins for testing purposes"""

    cache: Cache
    datetime: Datetime
    request: Request
    database: Database
    check: Check
    format: Format
    _parent: APITestCase
    fake: Faker

    def __init__(self, parent) -> None:
        self._parent = parent

        self.cache = Cache(parent)
        self.datetime = Datetime(parent)
        self.request = Request(parent)
        self.database = Database(parent)
        self.check = Check(parent)
        self.format = Format(parent)
        self.fake = Faker()

    def help(self, *args) -> None:
        """
        Print a list of mixin with a tree style (command of Linux).

        Usage:

        ```py
        # this print a tree with all the mixins
        self.bc.help()

        # this print just the docs of corresponding method
        self.bc.help('bc.datetime.now')
        ```
        """

        if args:
            for arg in args:
                self._get_doctring(arg)

        else:
            self._help_tree()

        # prevent left a `self.bc.help()` in the code
        assert False

    def _get_doctring(self, path: str) -> None:
        parts_of_path = path.split('.')
        current_path = ''
        current = None

        for part_of_path in parts_of_path:
            if not current:
                if not hasattr(self._parent, part_of_path):
                    current_path += f'.{part_of_path}'
                    break

                current = getattr(self._parent, part_of_path)

            else:
                if not hasattr(current, part_of_path):
                    current_path += f'.{part_of_path}'
                    current = None
                    break

                current = getattr(current, part_of_path)

        if current:
            from unittest.mock import patch, MagicMock

            if callable(current):
                print(f'self.{path}{print_arguments(current)}:')
            else:
                print(f'self.{path}:')

            print()

            with patch('sys.stdout.write', MagicMock()) as mock:
                help(current)

            for args, _ in mock.call_args_list:
                if args[0] == '\n':
                    print()
                lines = args[0].split('\n')

                for line in lines[3:-1]:
                    print(f'    {line}')

        else:
            print(f'self.{path}:')
            print()
            print(f'    self{current_path} not exists.')

        print()

    def _help_tree(self, level: int = 0, parent: Optional[dict] = None, last_item: bool = False) -> list[str]:
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
                result = [*result, *Breathecode._help_tree(item, level + 1, item, last_item)]

        result[-1] = result[-1].replace('  ├── ', '  └── ')
        result[-1] = result[-1].replace(r'├── ([a-zA-Z0-9]+)$', r'└── \1')

        for n in range(len(result) - 1, -1, -1):
            if result[n][0] == '├':
                result[n] = re.sub(r'^├', r'└', result[n])
                break

        if level == 0:
            print('\n'.join(result))

        return result
