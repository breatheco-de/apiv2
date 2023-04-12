#!/usr/bin/env bash

python -m scripts.install
docker-compose up -d redis postgres
pipenv run migrate
pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json
