from __future__ import absolute_import, unicode_literals

import os
import ssl
from celery import Celery
from celery.signals import task_failure

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')
REDIS_URL = os.getenv('REDIS_URL', '')

# fix ssl error
kwargs = {} if REDIS_URL.startswith('redis://') else {
    'broker_use_ssl': {
        'ssl_cert_reqs': ssl.CERT_NONE,
    },
    'redis_backend_use_ssl': {
        'ssl_cert_reqs': ssl.CERT_NONE,
    },
}

app = Celery('celery_breathecode', **kwargs)

if os.getenv('ENV') == 'test':
    app.conf.update(task_always_eager=True)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')
app.conf.update(BROKER_URL=REDIS_URL, CELERY_RESULT_BACKEND=REDIS_URL, namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

if bool(os.environ.get('CELERY_WORKER_RUNNING', False)) and REDIS_URL:
    from django.conf import settings
    import rollbar
    rollbar.init(**settings.ROLLBAR)

    def celery_base_data_hook(request, data):
        data['framework'] = 'celery'

    rollbar.BASE_DATA_HOOK = celery_base_data_hook

    @task_failure.connect
    def handle_task_failure(**kw):
        rollbar.report_exc_info(extra_data=kw)
