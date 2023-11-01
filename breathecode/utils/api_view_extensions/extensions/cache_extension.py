import logging
from typing import Optional
from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.response_order import ResponseOrder
from breathecode.utils.cache import Cache
from django.http import HttpResponse
from rest_framework import status

__all__ = ['CacheExtension']

logger = logging.getLogger(__name__)


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
        extends = {
            'request.path': self._request.path,
        }

        if self._cache_per_user:
            extends['request.user.id'] = self._request.user.id

        if lang := self._request.META.get('HTTP_ACCEPT_LANGUAGE'):
            extends['request.headers.accept-language'] = lang

        if accept := self._request.META.get('HTTP_ACCEPT'):
            extends['request.headers.accept'] = accept

        if self._cache_prefix:
            extends['breathecode.view.get'] = self._cache_prefix

        return {**self._request.GET.dict(), **self._request.parser_context['kwargs'], **extends}

    def get(self) -> dict:
        # allow requests to disable cache with querystring "cache" variable
        cache_is_active = self._request.GET.get('cache', 'true').lower() in ['true', '1', 'yes']
        if not cache_is_active:
            logger.debug('Cache has been forced to disable')
            return None

        try:
            params = self._get_params()
            res = self._cache.get(params)

            if res is None:
                return None

            data, mime, headers = res
            response = HttpResponse(data, content_type=mime, status=status.HTTP_200_OK, headers=headers)
            return response

        except Exception:
            logger.exception('Error while trying to get the cache')
            return None

    def _get_order_of_response(self) -> int:
        return int(ResponseOrder.CACHE)

    def _can_modify_response(self) -> bool:
        return True

    def _apply_response_mutation(self,
                                 data: list[dict] | dict,
                                 headers: Optional[dict] = None,
                                 format='application/json'):
        if headers is None:
            headers = {}

        params = self._get_params()

        try:
            res = self._cache.set(data, format=format, **params)
            data = res['data']
            headers = {
                **headers,
                **res['headers'],
            }

        except Exception:
            logger.exception('Error while trying to set the cache')

        return (data, headers)
