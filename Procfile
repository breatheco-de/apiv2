release: python manage.py migrate && python manage.py create_roles
worker: export CELERY_WORKER_RUNNING=True; celery -A breathecode.celery worker --loglevel=INFO
web: gunicorn breathecode.wsgi
