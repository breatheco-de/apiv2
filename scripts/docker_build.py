#!/bin/env python

from __future__ import absolute_import

import os
import sys


def run():
    exit_code = os.system("docker build ./ -t breathecode --rm=false")

    if exit_code:
        sys.exit(1)
