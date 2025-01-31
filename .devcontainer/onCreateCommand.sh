#!/usr/bin/env bash

python -m scripts.install
docker-compose up -d redis postgres
poetry run migrate
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
poetry run python manage.py create_academy_roles
docker-compose down
