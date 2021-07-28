#!/bin/env python

from __future__ import absolute_import

import os
import sys

if __name__ == '__main__':
    exit_code = os.system(
        'docker build ./ -t breathecode-environment --rm=false -f ./Dockerfile.environment')

    if exit_code:
        sys.exit(1)
