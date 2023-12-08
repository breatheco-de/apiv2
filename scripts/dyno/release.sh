#!/bin/env bash

HIDE_CACHE_LOG=${HIDE_CACHE_LOG:-1}

export CORALOGIX_SUBSYSTEM=release;
python manage.py migrate
python manage.py create_academy_roles
python manage.py set_permissions
