#!/bin/env python

from __future__ import absolute_import
import os
import random
import sys

if __name__ == '__main__':
    args = ''

    if len(sys.argv) > 1:
        sys.argv.pop(0)
        args = ' '.join(sys.argv)

    # this fix a problem caused by the geniuses at pytest-xdist
    seed = random.randint(0, 4294967295)
    command = f'pytest {args} --disable-pytest-warnings -n auto --nomigrations --durations=1'

    # unix like support
    exit_code = os.system(f'export RANDOM={seed}; {command}')

    # python don't return 256
    if exit_code:
        sys.exit(1)
