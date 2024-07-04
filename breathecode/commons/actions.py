import functools
import logging
import os

from django_redis import get_redis_connection
from redis.lock import Lock

from breathecode.utils import Cache
from breathecode.utils.cache import CACHE_DEPENDENCIES, CACHE_DESCRIPTORS

logger = logging.getLogger(__name__)

__all__ = ["clean_cache"]


def is_test():
    """Get the environment. It fix a error caused by pytest or python."""
    env = os.getenv("ENV")
    if env is None and "ENV" in os.environ:
        env = os.environ["ENV"]

    return env == "test"


@functools.lru_cache(maxsize=1)
def is_output_enable():
    # Set to True to enable output within the cache and it's used for testing purposes.
    return os.getenv("HIDE_CACHE_LOG", "0") in ["0", "false", "False", "f"]


def clean_cache(model_cls):
    from .tasks import clean_task

    have_descriptor = model_cls in CACHE_DESCRIPTORS.keys()
    is_a_dependency = model_cls in CACHE_DEPENDENCIES

    if not have_descriptor and not is_a_dependency:
        if is_output_enable():
            logger.warning(f"Cache not implemented for {model_cls.__name__}, skipping")
        return

    key = model_cls.__module__ + "." + model_cls.__name__

    # build a descriptor
    if not have_descriptor and is_a_dependency:
        if is_test() is False:
            conn = get_redis_connection("default")
            my_lock = Lock(conn, f"cache:descriptor:{key}", timeout=30, blocking_timeout=30)

            if my_lock.acquire(blocking=True):

                try:

                    class DepCache(Cache):
                        model = model_cls
                        is_dependency = True

                finally:
                    my_lock.release()

            else:
                if is_output_enable():
                    logger.error(f"Could not acquire lock for {key} on get_or_create, operation timed out.")
                return

        else:

            class DepCache(Cache):
                model = model_cls
                is_dependency = True

    key = model_cls.__module__ + "." + model_cls.__name__
    clean_task.apply_async(args=[key], countdown=0)
