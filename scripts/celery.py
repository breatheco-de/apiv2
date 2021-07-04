#!/bin/env python

import os
import sys
from pathlib import Path
from .utils.environment import celery_worker_environment

if __name__ == '__main__':
    celery_worker_environment()
    exit_code = os.system(
        f'celery -A breathecode.celery worker --loglevel=INFO')

    # python don't return 256
    if exit_code:
        sys.exit(1)
