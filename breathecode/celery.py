from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from breathecode.setup import get_redis_config

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')

settings, kwargs, REDIS_URL = get_redis_config()

app = Celery('celery_breathecode', **kwargs)
if os.getenv('ENV') == 'test':
    app.conf.update(task_always_eager=True)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')
app.conf.update(BROKER_URL=REDIS_URL, CELERY_RESULT_BACKEND=REDIS_URL, namespace='CELERY', result_expires=10)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
