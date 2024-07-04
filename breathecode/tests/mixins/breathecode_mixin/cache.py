from __future__ import annotations

from rest_framework.test import APITestCase

from ..cache_mixin import CacheMixin
from . import interfaces

__all__ = ["Cache"]


class Cache:
    """Mixin with the purpose of cover all the related with cache"""

    clear = CacheMixin.clear_cache
    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc
