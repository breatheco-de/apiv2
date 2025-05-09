#!/usr/bin/env bash

docker compose up -d

./scripts/utils/wait-port.sh localhost 5432
./scripts/utils/wait-port.sh localhost 6379

poetry run migrate
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
poetry run python manage.py create_academy_roles
