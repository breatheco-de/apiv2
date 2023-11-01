import logging
from django_redis import get_redis_connection
from redis.lock import Lock
from breathecode.utils import Cache

from breathecode.utils.cache import CACHE_DESCRIPTORS, CACHE_DEPENDENCIES

logger = logging.getLogger(__name__)

__all__ = ['clean_cache']


def clean_cache(model_cls):
    ...
    from .tasks import clean_task

    have_descriptor = model_cls in CACHE_DESCRIPTORS.keys()
    is_a_dependency = model_cls in CACHE_DEPENDENCIES

    if not have_descriptor and not is_a_dependency:
        logger.warn(f'Cache not implemented for {model_cls.__name__}, skipping')
        return

    conn = get_redis_connection('default')
    key = model_cls.__module__ + '.' + model_cls.__name__

    # build a descriptor
    if not have_descriptor and is_a_dependency:
        my_lock = Lock(conn, f'cache:descriptor:{key}', timeout=0.2, blocking_timeout=0.2)

        if my_lock.acquire(blocking=True):
            try:

                class _(Cache):
                    model = model_cls
                    is_dependency = True

            finally:
                my_lock.release()
        else:
            logger.error(f'Could not acquire lock for {key} on get_or_create, operation timed out.')
            return

    key = model_cls.__module__ + '.' + model_cls.__name__
    clean_task.apply_async(args=[key], countdown=0, priority=10)
