from collections import OrderedDict
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param, remove_query_param

__all__ = ["HeaderLimitOffsetPagination"]


class HeaderLimitOffsetPagination(LimitOffsetPagination):

    def paginate_queryset(self, queryset, request, view=None):
        self.use_envelope = True
        if str(request.GET.get("envelope")).lower() in ["false", "0"]:
            self.use_envelope = False
        result = self._paginate_queryset(queryset, request, view)
        if hasattr(queryset, "filter"):
            return result
        return queryset

    def _paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.count = self.get_count(queryset)
        self.offset = self.get_offset(request)
        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        # if self.count == 0 or self.offset > self.count:
        #     return []
        return queryset[self.offset : self.offset + self.limit]

    def __parse_comma__(self, string: str):
        if not string:
            return None

        return string.replace("%2C", ",")

    def get_paginated_response(self, data, count=None, cache=None, cache_kwargs=None):
        if cache_kwargs is None:
            cache_kwargs = {}

        if count:
            self.count = count

        next_url = self.__parse_comma__(self.get_next_link())
        previous_url = self.__parse_comma__(self.get_previous_link())
        first_url = self.__parse_comma__(self.get_first_link())
        last_url = self.__parse_comma__(self.get_last_link())

        links = []
        for label, url in (
            ("first", first_url),
            ("next", next_url),
            ("previous", previous_url),
            ("last", last_url),
        ):
            if url is not None:
                links.append('<{}>; rel="{}"'.format(url, label))

        headers = {"Link": ", ".join(links)} if links else {}
        headers["x-total-count"] = self.count

        if self.use_envelope:
            data = OrderedDict(
                [
                    ("count", self.count),
                    ("first", first_url),
                    ("next", next_url),
                    ("previous", previous_url),
                    ("last", last_url),
                    ("results", data),
                ]
            )

        if cache:
            cache.set(data, **cache_kwargs)

        return Response(data, headers=headers)

    def get_first_link(self):
        if self.offset <= 0:
            return None

        url = self.request.build_absolute_uri()
        return remove_query_param(url, self.offset_query_param)

    def get_last_link(self):
        if self.offset + self.limit >= self.count:
            return None

        url = self.request.build_absolute_uri()
        url = replace_query_param(url, self.limit_query_param, self.limit)
        offset = self.count - self.limit
        return replace_query_param(url, self.offset_query_param, offset)

    def is_paginate(self, request):
        return request.GET.get(self.limit_query_param) or request.GET.get(self.offset_query_param)

    def pagination_params(self, request):
        return {
            self.limit_query_param: request.GET.get(self.limit_query_param),
            self.offset_query_param: request.GET.get(self.offset_query_param),
        }
