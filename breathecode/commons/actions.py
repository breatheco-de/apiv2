from breathecode.utils import CACHE_DESCRIPTORS

__all__ = ['clean_cache']


def clean_cache(key):
    if key in CACHE_DESCRIPTORS:
        cache = CACHE_DESCRIPTORS[key]
        cache.clear()
