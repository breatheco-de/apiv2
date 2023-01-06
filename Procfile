release: export CORALOGIX_SUBSYSTEM=release; python manage.py migrate && python manage.py create_academy_roles && python manage.py set_permissions && python manage.py loaddata breathecode/*/fixtures/dev_*.json || true
celeryworker: export CORALOGIX_SUBSYSTEM=celeryworker; export CELERY_WORKER_RUNNING=True; celery -A breathecode.celery worker --loglevel=INFO
channelsworker: export CORALOGIX_SUBSYSTEM=channelsworker; python manage.py runworker channel_layer -v2
web: export CORALOGIX_SUBSYSTEM=web; daphne breathecode.asgi:application --port $PORT --bind 0.0.0.0 -v2
