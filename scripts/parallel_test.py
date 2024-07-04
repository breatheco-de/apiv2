#!/bin/env python

from __future__ import absolute_import

import os
import subprocess
import sys

if __name__ == "__main__":
    args = ""

    if len(sys.argv) > 1:
        sys.argv.pop(0)
        args = " ".join(sys.argv)

    command = f"pytest {args} --disable-pytest-warnings -n auto --nomigrations --durations=1"
    # command = f'pytest {pytest_args} -n auto --nomigrations --durations=1'

    env = os.environ.copy()
    env["ENV"] = "test"

    exit_code = subprocess.run(command, env=env, shell=True).returncode

    # python doesn't return 256
    if exit_code:
        sys.exit(1)
