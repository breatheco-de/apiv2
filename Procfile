release: pdm install && pdm run python manage.py migrate && pdm run python manage.py create_academy_roles && pdm run python manage.py set_permissions
worker: export CELERY_WORKER_RUNNING=True; pdm run celery -A breathecode.celery worker --loglevel=INFO
web: pdm run gunicorn breathecode.wsgi
