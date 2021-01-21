#!/bin/env bash

# script doesn't run if one command fail
set -euo pipefail

echo ""
echo "collect statics"
python manage.py collectstatic --noinput

echo ""
echo "migrate"
python manage.py migrate

echo ""
echo "load fixtures"
python manage.py loaddata breathecode/*/fixtures/dev_*.json

echo ""
echo "run server"
gunicorn --bind :8000 --workers 3 breathecode.wsgi:application
