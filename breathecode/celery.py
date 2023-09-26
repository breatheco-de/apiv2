from __future__ import absolute_import, unicode_literals
import os
import ssl
from celery import Celery
from celery.signals import task_failure

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')
	@@ -29,7 +28,12 @@
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')
app.conf.update(BROKER_URL=REDIS_URL, CELERY_RESULT_BACKEND=REDIS_URL, namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
