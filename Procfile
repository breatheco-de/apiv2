release: python manage.py migrate && python manage.py create_academy_roles && python manage.py set_permissions
celeryworker: export CELERY_WORKER_RUNNING=True; celery -A breathecode.celery worker --loglevel=INFO
channelsworker: python manage.py runworker channel_layer -v2
web: daphne breathecode.asgi:application --port $PORT --bind 0.0.0.0 -v2
