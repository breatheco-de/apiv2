#!/usr/bin/env bash

poetry python install $(cat ./.python-version)
poetry env use $(cat ./.python-version)

python -m scripts.install

sudo docker compose up -d redis postgres
poetry run migrate
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
poetry run python manage.py create_academy_roles
sudo docker compose down
