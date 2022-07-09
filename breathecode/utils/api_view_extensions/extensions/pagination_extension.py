import inspect
from collections import OrderedDict
from typing import Any
from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.mutator_order import MutatorOrder
from breathecode.utils.api_view_extensions.priorities.response_order import ResponseOrder
from breathecode.utils.cache import Cache
from breathecode.utils.exceptions import ProgramingError
from django.db.models import QuerySet
from rest_framework.utils.urls import replace_query_param, remove_query_param
from django.core.handlers.wsgi import WSGIRequest

__all__ = ['PaginationExtension']

REQUIREMENTS = ['cache']
OFFSET_QUERY_PARAM = 'offset'
LIMIT_QUERY_PARAM = 'limit'
MAX_LIMIT = None
DEFAULT_LIMIT = 100


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        return min(ret, cutoff)
    return ret


class PaginationExtension(ExtensionBase):

    _count: int
    _offset: int
    _use_envelope: bool
    _paginate: bool

    def __init__(self, paginate: bool, **kwargs) -> None:
        self._paginate = paginate

    def _can_modify_queryset(self) -> bool:
        return self._paginate

    def _get_order_of_mutator(self) -> int:
        return MutatorOrder.PAGINATION

    def _can_modify_response(self) -> bool:
        return self._paginate and self._is_paginate()

    def _get_order_of_response(self) -> int:
        return int(ResponseOrder.PAGINATION) if self._is_paginate() else -1

    def _is_paginate(self):
        return bool(self._request.GET.get(LIMIT_QUERY_PARAM) or self._request.GET.get(OFFSET_QUERY_PARAM))

    def _apply_queryset_mutation(self, queryset: QuerySet[Any]):
        if not self._is_paginate():
            return queryset[0:DEFAULT_LIMIT]

        self._use_envelope = True
        if str(self._request.GET.get('envelope')).lower() in ['false', '0']:
            self._use_envelope = False

        self._count = self._get_count(queryset)
        self._offset = self._get_offset()
        self._limit = self._get_limit()
        return queryset[self._offset:self._offset + self._limit]

    def _apply_response_mutation(self, data: list[dict] | dict, headers: dict = {}):
        next_url = self._parse_comma(self._get_next_link())
        previous_url = self._parse_comma(self._get_previous_link())
        first_url = self._parse_comma(self._get_first_link())
        last_url = self._parse_comma(self._get_last_link())

        links = []
        for label, url in (
            ('first', first_url),
            ('next', next_url),
            ('previous', previous_url),
            ('last', last_url),
        ):
            if url is not None:
                links.append('<{}>; rel="{}"'.format(url, label))

        headers = {**headers, 'Link': ', '.join(links)} if links else {**headers}
        headers['x-total-count'] = self._count

        if self._use_envelope:
            data = OrderedDict([('count', self._count), ('first', first_url), ('next', next_url),
                                ('previous', previous_url), ('last', last_url), ('results', data)])
            return (data, headers)

        return (data, headers)

    def _parse_comma(self, string: str):
        if not string:
            return None

        return string.replace('%2C', ',')

    def _get_count(self, queryset: QuerySet[Any] | list):
        """
        Determine an object count, supporting either querysets or regular lists.
        """

        try:
            return queryset.count()
        except (AttributeError, TypeError):
            return len(queryset)

    def _get_limit(self):
        if LIMIT_QUERY_PARAM:
            try:
                return _positive_int(self._request.query_params[LIMIT_QUERY_PARAM],
                                     strict=True,
                                     cutoff=MAX_LIMIT)
            except (KeyError, ValueError):
                pass

        return DEFAULT_LIMIT

    def _get_offset(self):
        try:
            return _positive_int(self._request.query_params[OFFSET_QUERY_PARAM])
        except (KeyError, ValueError):
            return 0

    def _get_first_link(self):
        if self._offset <= 0:
            return None

        url = self._request.build_absolute_uri()
        return remove_query_param(url, OFFSET_QUERY_PARAM)

    def _get_last_link(self):
        if self._offset + self._limit >= self._count:
            return None

        url = self._request.build_absolute_uri()
        url = replace_query_param(url, LIMIT_QUERY_PARAM, self._limit)
        offset = self._count - self._limit
        return replace_query_param(url, OFFSET_QUERY_PARAM, offset)

    def _get_next_link(self):
        if self._offset + self._limit >= self._count:
            return None

        url = self._request.build_absolute_uri()
        url = replace_query_param(url, LIMIT_QUERY_PARAM, self._limit)

        offset = self._offset + self._limit
        return replace_query_param(url, OFFSET_QUERY_PARAM, offset)

    def _get_previous_link(self):
        if self._offset <= 0:
            return None

        url = self._request.build_absolute_uri()
        url = replace_query_param(url, LIMIT_QUERY_PARAM, self._limit)

        if self._offset - self._limit <= 0:
            return remove_query_param(url, OFFSET_QUERY_PARAM)

        offset = self._offset - self._limit
        return replace_query_param(url, OFFSET_QUERY_PARAM, offset)
