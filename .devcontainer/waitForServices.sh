#!/usr/bin/env bash

docker compose up -d

./scripts/utils/wait-port.sh localhost 5432
./scripts/utils/wait-port.sh localhost 6379
