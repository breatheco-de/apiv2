#!/bin/env bash

# script doesn't run if one command fail
set -euo pipefail

python manage.py collectstatic --noinput
python manage.py migrate
gunicorn --bind :8000 --workers 3 breathecode.wsgi:application
