release: python manage.py migrate && python manage.py create_academy_roles && python manage.py set_permissions
worker: export CELERY_WORKER_RUNNING=True; celery -A breathecode.celery worker --loglevel=INFO
web: daphne breathecode.asgi:application --port $PORT --bind 0.0.0.0 -v2
