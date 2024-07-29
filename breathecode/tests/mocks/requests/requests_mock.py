"""Requests mock."""

from unittest.mock import Mock

from .response_mock import ResponseMock


def request_mock(endpoints=None):
    if endpoints is None:
        endpoints = []

    def base(url: str, *args, **kwargs):
        """Requests get mock."""

        if (
            url == "GET"
            or url == "POST"
            or url == "PUT"
            or url == "PATCH"
            or url == "DELETE"
            or url == "HEAD"
            or url == "REQUEST"
        ):
            url = args[0]

        if len(endpoints[0]) == 4:
            match = [(status, data, headers) for (status, endpoint, data, headers) in endpoints if url == endpoint]
        else:
            match = [(status, data) for (status, endpoint, data) in endpoints if url == endpoint]

        headers = None
        if match:
            if len(endpoints[0]) == 4:
                (status, data, headers) = match[0]
            else:
                (status, data) = match[0]
            return ResponseMock(data=data, status_code=status, url=url, request_headers=headers)

        return ResponseMock(data="not fount", status_code=404)

    return Mock(side_effect=base)
