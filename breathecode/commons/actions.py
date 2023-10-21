import logging
from breathecode.utils import CACHE_DESCRIPTORS

logger = logging.getLogger(__name__)

__all__ = ['clean_cache']


def clean_cache(key):
    from .tasks import clean_task

    if key in CACHE_DESCRIPTORS:
        cache = CACHE_DESCRIPTORS[key]

        try:
            cache.clear()

        except Exception:
            clean_task.apply_async(args=[key], countdown=5, priority=10)
