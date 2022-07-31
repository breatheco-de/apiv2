__all__ = ['FakeRequest']

from typing import Any
from rest_framework import HTTP_HEADER_ENCODING


class FakeRequest:
    META: dict[bytes, bytes]
    headers: dict[str | bytes, bytes]
    ws_request: bool

    def __init__(self, obj: dict[bytes, bytes]):
        self.META = {}
        self.headers = {}
        self.ws_request = True

        for key in obj:
            self.META[f'HTTP_{key.decode(HTTP_HEADER_ENCODING).upper()}'] = obj[key]
            self.headers[key.decode(HTTP_HEADER_ENCODING)] = obj[key].decode(HTTP_HEADER_ENCODING)

    def set_user(self, user):
        self.user = user
