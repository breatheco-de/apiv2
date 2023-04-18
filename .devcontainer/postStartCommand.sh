#!/usr/bin/env bash

docker-compose up -d redis postgres
pipenv run start
