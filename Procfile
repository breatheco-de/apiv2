release: python manage.py migrate
worker: export CELERY_WORKER_RUNNING=True; celery -A breathecode.celery worker --loglevel=INFO
web: gunicorn breathecode.wsgi