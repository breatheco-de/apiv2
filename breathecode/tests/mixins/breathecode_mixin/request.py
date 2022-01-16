from ..headers_mixin import HeadersMixin

__all__ = ['Request']


class Request:
    """Wrapper of last implementation for request for testing purposes"""

    set_headers = HeadersMixin.headers
