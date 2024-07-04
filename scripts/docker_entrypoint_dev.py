#!/bin/env python

from __future__ import absolute_import

import os
import sys


def execute(command):
    exit_code = os.system(command)

    if exit_code:
        sys.exit(1)


if __name__ == "__main__":
    print("")
    print("fix .env")
    execute("python -m scripts.hooks.postinstall.generate_environment")

    print("")
    print("Collect statics")
    execute("sudo chown shell -R staticfiles")
    execute("sudo chmod 777 -R staticfiles")
    execute("pipenv run python manage.py collectstatic --noinput")

    print("")
    print("Migrate")
    execute("pipenv run python manage.py migrate")

    print("")
    print("Load fixtures")
    execute("pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json")

    print("")
    print("Run server")
    execute("pipenv run python manage.py runserver 0.0.0.0:8000")
