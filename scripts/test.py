#!/bin/env python

from __future__ import absolute_import

import os
import sys

if __name__ == "__main__":
    args = ""

    if len(sys.argv) > 1:
        sys.argv.pop(0)
        args = " ".join(sys.argv)

    # exit_code = os.system(f'pytest {args} --disable-pytest-warnings --nomigrations --durations=1')
    exit_code = os.system(f"pytest {args} --nomigrations --durations=1")

    # python don't return 256
    if exit_code:
        sys.exit(1)
