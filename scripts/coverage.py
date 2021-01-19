#!/bin/env python

import os, sys
from pathlib import Path


def python_module_to_dir(module: str) -> str:
    parsed_dir = '/'.join(module.split('.'))
    return Path(f'./{parsed_dir}').resolve()


def help_command():
    print('Usage:')
    print('   `pipenv run breathecode.events` where events is the name of module and accept '
        'add submodules using the dot(.) character as delimiter.')
    print('')
    print('commands:')
    print('   --help see this help message.')
    exit()


module = 'breathecode'

if len(sys.argv) > 1:
    module = sys.argv[1]

    if module == '--help' or module == '-h':
        help_command()

dir = python_module_to_dir(module)

os.system(f'pytest {dir} --disable-pytest-warnings --cov={module} --cov-report html')
