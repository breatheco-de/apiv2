"""
Cache mixin
"""
from django.core.cache import cache

__all__ = ['CacheMixin']


class CacheMixin():
    """Cache mixin"""
    def clear_cache(self) -> None:
        cache.clear()
