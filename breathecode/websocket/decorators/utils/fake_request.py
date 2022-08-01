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
        self.GET = {}
        self.parser_context = {'args': (), 'kwargs': {}}
        self.ws_request = True

        for key in obj:
            k = key
            if isinstance(k, bytes):
                k = k.decode(HTTP_HEADER_ENCODING)

            self.META[f'HTTP_{k.upper()}'] = obj[key]
            self.headers[k] = obj[k]

            if isinstance(self.headers[k], bytes):
                self.headers[k] = self.headers[k].decode(HTTP_HEADER_ENCODING)

    def set_user(self, user):
        self.user = user

    def get_full_path(self):
        return '/'
