from typing import Optional
from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.response_order import ResponseOrder
from breathecode.utils.cache import Cache

__all__ = ['CacheExtension']


class CacheExtension(ExtensionBase):

    _cache: Cache

    def __init__(self, cache: Cache, **kwargs) -> None:
        self._cache = cache()

    def _instance_name(self) -> Optional[str]:
        return 'cache'

    def _get_params(self):
        return {**self._request.GET.dict(), **self._request.parser_context['kwargs']}

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
