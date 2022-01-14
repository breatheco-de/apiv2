"""
Cache mixin
"""
from django.core.cache import cache


class CacheMixin():
    """Cache mixin"""
    def clear_cache(self, **kargs):
        cache.clear()

    def tearDown(self):
        self.clear_cache()
