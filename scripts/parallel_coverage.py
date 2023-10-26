#!/bin/env python

import os
import random
import sys
import shutil
import webbrowser
from pathlib import Path


def python_module_to_dir(module: str) -> str:
    parsed_dir = '/'.join(module.split('.'))
    return Path(f'./{parsed_dir}').resolve()


def help_command():
    print('Usage:')
    print('   `pipenv run cov breathecode.events` where events is the name of module and accept '
          'add submodules using the dot(.) character as delimiter.')
    print('')
    print('commands:')
    print('   --help see this help message.')
    exit()


if __name__ == '__main__':
    module = 'breathecode'

    if len(sys.argv) > 3:
        module = sys.argv[3]

        if module == '--help' or module == '-h':
            help_command()

    dir = python_module_to_dir(module)

    htmlcov_path = os.path.join(os.getcwd(), 'htmlcov')

    if os.path.exists(htmlcov_path):
        shutil.rmtree(htmlcov_path)

    # this fix a problem caused by the geniuses at pytest-xdist
    seed = random.randint(0, 4294967295)
    command = (f'pytest {dir} --disable-pytest-warnings {sys.argv[1]} {sys.argv[2]} '
               f'--cov={module} --cov-report html -n auto --nomigrations --durations=1')

    # unix like support
    exit_code = os.system(f'export RANDOM={seed}; {command}')

    webbrowser.open('file://' + os.path.realpath(os.path.join(os.getcwd(), 'htmlcov', 'index.html')))

    # python don't return 256
    if exit_code:
        sys.exit(1)
