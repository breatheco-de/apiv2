from __future__ import absolute_import, unicode_literals

# keeps this adobe
import newrelic.agent

newrelic.agent.initialize()

# the rest of your Celery file contents go here
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
app.conf.update(broker_url=REDIS_URL,
                result_backend=REDIS_URL,
                namespace='CELERY',
                result_expires=10,
                worker_max_memory_per_child=int(os.getenv('CELERY_MAX_MEMORY_PER_WORKER', '470000')),
                worker_max_tasks_per_child=int(os.getenv('CELERY_MAX_TASKS_PER_WORKER', '1000')))

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.conf.broker_transport_options = {
    'priority_steps': list(range(11)),
    'sep': ':',
    'queue_order_strategy': 'priority',
}

app.conf.task_default_priority = 5  # Default priority value
