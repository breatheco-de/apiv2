from aiohttp_retry import Optional
import pytest
from typing import Generator, Self

# not implemented yet
supported_http_clients = []

try:
    import requests

    supported_http_clients.append("requests")
except ImportError:
    ...

try:
    import aiohttp

    supported_http_clients.append("aiohttp")
except ImportError:
    ...


__all__ = ["http", "HTTP"]


class ResponseGenerator:
    def __init__(self, method: str, is_request: bool, endpoints: list[tuple[str, dict]]):
        self._method = method
        self._is_request = is_request
        self._endpoints = endpoints

    def request(self, url: str, **kwargs) -> Self:
        self._url = url
        self._kwargs = kwargs
        return self

    def response(self, data, status: int = 200, headers: Optional[dict] = None) -> None:
        if headers is None:
            headers = {}

        self._endpoints.append((self._method, self._url, self._kwargs, data, status, headers))


class AsyncResponseMock:

    def __init__(self, data=None, status=200, headers=None, json=None):
        if json is not None:
            data = json

        if headers is None:
            headers = {}

        self.content = data
        self.status = status
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self.content


class ResponseMock:

    def __init__(self, data=None, json=None, status=200, headers=None):
        if json is not None:
            data = json

        if headers is None:
            headers = {}

        self.content = data
        self.status = status
        self.headers = headers

    def json(self):
        return self.content


class HTTP:
    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        self._monkeypatch = monkeypatch

        self.call_count = 0

        self._get = []
        self._post = []
        self._put = []
        self._delete = []
        self._head = []
        self._request = []

    def _match(self, method: str, url: str, **kwargs):

        return self._get.get(url, {}).get(method, {}).get("kwargs", {}) == kwargs

    def _amatch(self, method: str, url: str, **kwargs):
        return self._get.get(url, {}).get(method, {}).get("kwargs", {}) == kwargs

    def enable(self):

        def get_endpoint(is_request, method, url, **kwargs):
            if is_request:
                endpoints = handlers["request"][0]
            else:
                key = method.lower()
                endpoints = handlers[key][0]

            key = (method, url, kwargs)
            for endpoint in endpoints:
                if key == (endpoint[0], endpoint[1], endpoint[2]):
                    return endpoint[3:]

            return None

        def match(is_request, method, url, kwargs):
            x = get_endpoint(is_request, method, url, **kwargs)
            if x is None:
                return ResponseMock({"error": "not found"}, status=404)

            self.call_count += 1

            return ResponseMock(data=x[0], status=x[1], headers=x[2])

        def amatch(is_request, method, url, kwargs):
            x = get_endpoint(is_request, method, url, **kwargs)
            if x is None:
                return AsyncResponseMock({"error": "not found"}, status=404)

            self.call_count += 1

            return AsyncResponseMock(x[0], x[1], x[2])

        handlers = {
            "get": (
                self._get,
                lambda url, **kwargs: match(is_request=False, method="GET", url=url, kwargs=kwargs),
                lambda url, **kwargs: amatch(is_request=False, method="GET", url=url, kwargs=kwargs),
            ),
            "post": (
                self._post,
                lambda url, **kwargs: match(is_request=False, method="POST", url=url, kwargs=kwargs),
                lambda self, url, **kwargs: amatch(is_request=False, method="POST", url=url, kwargs=kwargs),
            ),
            "put": (
                self._put,
                lambda url, **kwargs: match(is_request=False, method="PUT", url=url, kwargs=kwargs),
                lambda url, **kwargs: amatch(is_request=False, method="PUT", url=url, kwargs=kwargs),
            ),
            "delete": (
                self._delete,
                lambda url, **kwargs: match(is_request=False, method="DELETE", url=url, kwargs=kwargs),
                lambda url, **kwargs: amatch(is_request=False, method="DELETE", url=url, kwargs=kwargs),
            ),
            "head": (
                self._head,
                lambda url, **kwargs: match(is_request=False, method="HEAD", url=url, kwargs=kwargs),
                lambda url, **kwargs: amatch(is_request=False, method="HEAD", url=url, kwargs=kwargs),
            ),
            "request": (
                self._request,
                lambda method, url, **kwargs: match(is_request=True, method=method, url=url, kwargs=kwargs),
                lambda self, method, url, **kwargs: amatch(is_request=True, method=method, url=url, kwargs=kwargs),
            ),
        }

        for method, (_, handler, ahandler) in handlers.items():

            self._monkeypatch.setattr(aiohttp.ClientSession, method, ahandler)
            self._monkeypatch.setattr(requests, method, handler)

    def disable(self): ...

    def get(self, url: str, **kwargs) -> ResponseGenerator:
        return ResponseGenerator(method="GET", is_request=False, endpoints=self._get).request(url, **kwargs)

    def post(self, url: str, **kwargs) -> ResponseGenerator:
        return ResponseGenerator(method="POST", is_request=False, endpoints=self._post).request(url, **kwargs)

    def put(self, url: str, **kwargs) -> ResponseGenerator:
        return ResponseGenerator(method="PUT", is_request=False, endpoints=self._put).request(url, **kwargs)

    def delete(self, url: str, **kwargs) -> ResponseGenerator:
        return ResponseGenerator(method="DELETE", is_request=False, endpoints=self._delete).request(url, **kwargs)

    def head(self, url: str, **kwargs) -> ResponseGenerator:
        return ResponseGenerator(method="HEAD", is_request=False, endpoints=self._head).request(url, **kwargs)

    def _request_key(self, method: str, url: str):
        return (method, url)

    def request(self, method: str, url: str, **kwargs) -> ResponseGenerator:
        method = method.upper()
        return ResponseGenerator(method=method, is_request=True, endpoints=self._request).request(url, **kwargs)


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> Generator[HTTP, None, None]:
    http = HTTP(monkeypatch)

    http.enable()
    yield http
    http.disable()
