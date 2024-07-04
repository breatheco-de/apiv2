"""
Cache mixin
"""

from django.core.cache import cache

__all__ = ["CacheMixin"]


class CacheMixin:
    """Cache mixin"""

    def clear_cache(self) -> None:
        """
        Clear the cache.

        Usage:

        ```py
        self.bc.cache.clear()
        ```
        """
        cache.clear()
