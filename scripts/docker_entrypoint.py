#!/bin/env python

from __future__ import absolute_import

import os
import sys


def execute(command, required=True):
    exit_code = os.system(command)
    if exit_code and required:
        sys.exit(1)
    return exit_code == 0


if __name__ == "__main__":
    print("")
    print("Collect statics")
    execute("python manage.py collectstatic --noinput")

    print("")
    print("Migrate")
    execute("python manage.py migrate")

    print("")
    print("Load fixtures (optional; server will start even if fixtures fail)")
    execute("python manage.py loaddata breathecode/*/fixtures/dev_*.json", required=False)

    print("")
    print("Run server")
    execute("gunicorn --bind :8000 --workers 3 breathecode.wsgi:application")
