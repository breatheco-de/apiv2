from rest_framework import status
from rest_framework.response import Response
from breathecode.utils import HeaderLimitOffsetPagination, GenerateLookupsMixin
import os

IS_TEST_ENV = os.getenv('ENV') == 'test'


class CommonViewMixin(HeaderLimitOffsetPagination, GenerateLookupsMixin):
    __request__ = None
    __items__ = None
    __method__ = None
    __sort_by__ = None
    __ban_lookups__ = None
    __serializer__ = None

    def __apply_pagination__(self):
        if self.__method__ == 'GET' and isinstance(self.__items__, list):
            self.__items__.sort(self.__sort_by__)

    def __apply_lookups__(self):
        if self.__method__ == 'GET' and isinstance(self.__items__, list):
            lookups = {}
            for key in self.__request__.GET.keys():
                self.__request__.GET.get(key)

    def __apply_sort__(self):
        if self.__method__ == 'GET' and isinstance(self.__items__, list):
            self.__items__.sort(self.__sort_by__)

    def __clear_cache__(self):
        if self.__method__ != 'GET':
            self.cache.clear()

    def get_pagination(self):
        page = self.paginate_queryset(self.__items__, self.__request__)
        serializer = self.__serializer__(page, many=True)

        if self.is_paginate(self.__request__):
            return self.get_paginated_response(serializer.data,
                                               cache=self.cache,
                                               cache_kwargs=cache_kwargs)
        else:
            self.cache.set(serializer.data, **cache_kwargs)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def apply_commons(self,
                      request,
                      items,
                      serializer,
                      serializer_kwargs={},
                      sort='-created_at',
                      ban_lookups=[],
                      lookups={}):
        """
        apply_commons is used to handle the common feature that we supported
        in the views like paginations, filter lookups or sort_by
        """
        self.__request__ = request
        self.__items__ = items
        self.__method__ = request.method
        self.__ban_lookups__ = ban_lookups

        if sort:
            self.__sort_by__ = sort

        self.__apply_sort__()
        self.__clear_cache__()
