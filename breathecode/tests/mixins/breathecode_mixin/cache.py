from ..cache_mixin import CacheMixin

__all__ = ['Cache']


class Cache:
    """Wrapper of last implementation of cache mixin for testing purposes"""

    clear = CacheMixin.clear_cache

    def __init__(self, parent) -> None:
        self.parent = parent
