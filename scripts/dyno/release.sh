#!/bin/env bash

export CORALOGIX_SUBSYSTEM=release;
python manage.py migrate
python manage.py create_academy_roles
python manage.py set_permissions
