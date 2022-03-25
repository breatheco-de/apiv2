from rest_framework.test import APITestCase
from ..cache_mixin import CacheMixin

__all__ = ['Cache']


class Cache:
    """Mixin with the purpose of cover all the related with cache"""

    clear = CacheMixin.clear_cache
    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent
