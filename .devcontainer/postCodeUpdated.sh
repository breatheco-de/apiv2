#!/usr/bin/env bash

docker compose up -d

./scripts/utils/wait-port.sh localhost 5432
./scripts/utils/wait-port.sh localhost 6379

export HIDE_CACHE_LOG=1

poetry run migrate
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
poetry run python manage.py create_academy_roles

curl https://raw.githubusercontent.com/oh-my-fish/oh-my-fish/master/bin/install -o /tmp/install-omf.fish
fish /tmp/install-omf.fish --noninteractive -y
rm /tmp/install-omf.fish

fish -c "omf install fish-spec nvm foreign-env"
