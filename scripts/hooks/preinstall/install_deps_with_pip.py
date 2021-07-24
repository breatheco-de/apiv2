#!/bin/env python

import os
import sys

commands = ';\n'.join([
    'pip install --upgrade pip',
    'pip install --upgrade yapf pipenv',
    '',
])

exit_code = os.system(commands)

# python don't return 256
if exit_code:
    sys.exit(1)
