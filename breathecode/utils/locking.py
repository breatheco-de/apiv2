"""
Example usage:

class Bag(models.Model):
    # ... your fields here ...

    objects = LockManager()

# Usage with lock
bag, created = Bag.objects.get_or_create(
    lock=True,
    user=request.user,
    type=bag_type,
    academy=academy,
    currency=academy.main_currency
)

# Usage without lock
bag, created = Bag.objects.get_or_create(
    user=request.user,
    type=bag_type,
    academy=academy,
    currency=academy.main_currency
)
"""

from django.db import models, transaction
import os, redis
from redis.lock import Lock
from redis.exceptions import LockError
from breathecode.utils import getLogger
import ssl

logger = getLogger(__name__)
ENV = os.getenv('ENV', '')
REDIS_URL = os.getenv('REDIS_URL', '')

# Modify the connection_kwargs to disable SSL certificate verification ssl_cert_reqs="none"
redis_kwargs = {} if REDIS_URL.startswith('redis://') else {
    'ssl_cert_reqs': ssl.CERT_NONE,
}
redis_client = None


class LockManager(models.Manager):

    def get_or_create(self, lock=False, **kwargs):
        global redis_client

        instance, created = None, False

        if lock and ENV != 'test':
            if redis_client == None:
                redis_client = redis.from_url(REDIS_URL, **redis_kwargs)

            # Dynamically retrieve the class name and create a unique lock key based on the kwargs
            class_name = self.model.__name__
            lock_key_elements = [str(kwargs.get(key, '')) for key in sorted(kwargs.keys())]
            lock_key = f"{class_name}_lock:{'_'.join(lock_key_elements)}"

            try:
                with Lock(redis_client, lock_key, timeout=10, blocking_timeout=10):
                    with transaction.atomic():
                        instance, created = super().get_or_create(**kwargs)
            except LockError:
                # Handle the timeout, e.g., by logging, retrying, or returning an error
                logger = getLogger(
                    f'Could not acquire lock for {class_name} on get_or_create, operation timed out.')
                return None, False  # Indicate that the operation was not successful
        else:
            instance, created = super().get_or_create(**kwargs)

        return instance, created
