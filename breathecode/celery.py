from __future__ import absolute_import, unicode_literals
import os
import ssl
from celery import Celery

from breathecode.setup import configure_redis

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')

# production redis url
REDIS_URL = os.getenv('REDIS_COM_URL', '')
kwargs = {}

# local or heroku redis url
if REDIS_URL == '':
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # support for heroku redis addon
    if REDIS_URL.startswith('redis://'):
        kwargs = {
            'broker_use_ssl': {
                'ssl_cert_reqs': ssl.CERT_NONE,
            },
            'redis_backend_use_ssl': {
                'ssl_cert_reqs': ssl.CERT_NONE,
            }
        }

else:
    redis_ca_cert_path, redis_user_cert_path, redis_user_private_key_path = configure_redis()

    settings = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED,
        'ssl_ca_certs': redis_ca_cert_path,
        'ssl_certfile': redis_user_cert_path,
        'ssl_keyfile': redis_user_private_key_path,
    }

    kwargs = {
        'broker_use_ssl': settings,
        'redis_backend_use_ssl': settings,
    }

# overwrite the redis url with the new one
os.environ['REDIS_URL'] = REDIS_URL

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
