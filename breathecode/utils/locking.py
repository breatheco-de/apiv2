"""
Custom lock manager for Django models.

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

import os

from django.db import models, transaction
from redis.exceptions import LockError
from redis.lock import Lock

from breathecode.setup import get_redis
from breathecode.utils import getLogger

logger = getLogger(__name__)
ENV = os.getenv("ENV", "")
redis_client = None


# Actually this code didn't work because set up the right lock key is the key for the lock works, but appearly it's impossible
class LockManager(models.Manager):

    def get_or_create(self, lock=False, **kwargs):
        global redis_client

        instance, created = None, False

        if ENV != "test":

            if redis_client is None:
                redis_client = get_redis()

            # Dynamically retrieve the class name and create a unique lock key based on the kwargs
            class_name = self.model.__name__
            lock_key_elements = [str(kwargs.get(key, "")) for key in sorted(kwargs.keys())]
            lock_key = f"{class_name}_lock:{'_'.join(lock_key_elements)}"

            try:
                with Lock(redis_client, lock_key, timeout=30, blocking_timeout=30):
                    with transaction.atomic():
                        instance, created = super().get_or_create(**kwargs)
            except LockError:
                # Handle the timeout, e.g., by logging, retrying, or returning an error
                logger.error(f"Could not acquire lock for {class_name} on get_or_create, operation timed out.")
                return None, False  # Indicate that the operation was not successful
        else:
            instance, created = super().get_or_create(**kwargs)

        return instance, created
