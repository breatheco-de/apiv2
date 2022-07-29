#!/bin/env python

import os
import sys

exit_code = os.system('pdm run pre-commit install')

# python don't return 256
if exit_code:
    sys.exit(1)
