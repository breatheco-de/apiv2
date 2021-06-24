"""
Requests mock
"""
from unittest.mock import Mock
from .response_mock import ResponseMock


def request_mock(endpoints=[]):
    def base(url: str, **kwargs):
        """Requests get mock"""
        match = [(status, data) for (status, endpoint, data) in endpoints
                 if url == endpoint]

        if match:
            (status, data) = match[0]
            return ResponseMock(data=data, status_code=status, url=url)

        return ResponseMock(data='not fount', status_code=404)

    return Mock(side_effect=base)
