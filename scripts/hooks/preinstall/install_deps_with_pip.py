#!/bin/env python

import os
import sys
from time import sleep

from scripts.utils.get_pip_path import get_pip_path

pip_path = get_pip_path()
commands = ';\n'.join([
    f'{pip_path} install --upgrade pip',
    f'{pip_path} install --upgrade yapf pdm',
    '',
])

exit_code = os.system(commands)
print('PREINISTALL EXIT CODE', exit_code)

# python don't return 256
if exit_code:
    sys.exit(1)
