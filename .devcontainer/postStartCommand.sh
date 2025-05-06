#!/usr/bin/env bash

poetry python install $(cat ./.python-version)
poetry env use $(cat ./.python-version)

sudo docker compose up -d redis postgres
