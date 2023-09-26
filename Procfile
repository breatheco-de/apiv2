release: export CORALOGIX_SUBSYSTEM=release; python manage.py migrate && python manage.py create_academy_roles && python manage.py set_permissions
celeryworker: export CORALOGIX_SUBSYSTEM=celeryworker; export CELERY_WORKER_RUNNING=True; newrelic-admin run-program bin/start-pgbouncer-stunnel celery -A breathecode.celery worker --loglevel=INFO --concurrency 2 -E --maxtasksperchild=500
web: export CORALOGIX_SUBSYSTEM=web; newrelic-admin run-program bin/start-pgbouncer-stunnel gunicorn breathecode.wsgi --timeout 29 --workers 2 --max-requests 500 --max-requests-jitter 100 --worker-class gevent
