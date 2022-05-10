from typing import Optional
from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.response_order import ResponseOrder
from breathecode.utils.cache import Cache

__all__ = ['CacheExtension']


class CacheExtension(ExtensionBase):

    _cache: Cache
    _cache_per_user: bool
    _cache_prefix: str

    def __init__(self, cache: Cache, **kwargs) -> None:
        self._cache = cache()

    def _optional_dependencies(self, cache_per_user: bool = False, cache_prefix: str = '', **kwargs):
        self._cache_per_user = cache_per_user
        self._cache_prefix = cache_prefix

    def _instance_name(self) -> Optional[str]:
        return 'cache'

    def _get_params(self):
        extends = {}

        if self._cache_per_user:
            extends['request.user.id'] = self._request.user.id

        if self._cache_prefix:
            extends['breathecode.view.get'] = self._cache_prefix

        return {**self._request.GET.dict(), **self._request.parser_context['kwargs'], **extends}

    def get(self) -> dict:
        params = self._get_params()
        return self._cache.get(**params)

    def _get_order_of_response(self) -> int:
        return int(ResponseOrder.CACHE)

    def _can_modify_response(self) -> bool:
        return True

    def _apply_response_mutation(self, data: list[dict] | dict, headers: dict = {}):
        params = self._get_params()
        self._cache.set(data, **params)
        return (data, headers)
