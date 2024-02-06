from __future__ import annotations

from types import TracebackType
from typing import Any, Optional, Type

import aiohttp
import requests
from aiohttp.client_reqrep import ClientResponse
from asgiref.sync import sync_to_async

__all__ = ['Service']


class Service:

    def __init__(self, app_pk: str | int, user_pk: Optional[str | int] = None, *, mode: Optional[str] = None):
        from breathecode.authenticate.actions import get_app

        self.app = get_app(app_pk)

        self.user_pk = user_pk
        self.mode = mode

    def _sign(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        from breathecode.authenticate.actions import get_signature

        headers = kwargs.pop('headers', {})
        headers.pop('Authorization', None)

        sign, now = get_signature(self.app,
                                  self.user_pk,
                                  method=method,
                                  params=params,
                                  body=data if data is not None else json,
                                  headers=headers)

        headers['Authorization'] = (f'Signature App=4geeks,'
                                    f'Nonce={sign},'
                                    f'SignedHeaders={";".join(headers.keys())},'
                                    f'Date={now}')

        return headers

    def _jwt(self, method, **kwargs) -> requests.Request:
        from breathecode.authenticate.actions import get_jwt

        headers = kwargs.pop('headers', {})

        token = get_jwt(self.app, self.user_pk)

        headers['Authorization'] = (f'Link App=4geeks,'
                                    f'Token={token}')

        return headers

    def _authenticate(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        if self.mode == 'signature' or self.app.strategy == 'SIGNATURE':
            return self._sign(method, params=params, data=data, json=json, **kwargs)

        elif self.mode == 'jwt' or self.app.strategy == 'JWT':
            return self._jwt(method, **kwargs)

        raise Exception('Strategy not implemented')

    def _fix_url(self, url):
        if url[0] != '/':
            url = f'/{url}'

        return url

    def get(self, url, params=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('get', params=params, **kwargs)
        return requests.get(url, params=params, **kwargs, headers=headers)

    def options(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('options', **kwargs)
        return requests.options(url, **kwargs, headers=headers)

    def head(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('head', **kwargs)
        return requests.head(url, **kwargs, headers=headers)

    def post(self, url, data=None, json=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('post', data=data, json=json, **kwargs)
        return requests.post(url, data=data, json=json, **kwargs, headers=headers)

    def put(self, url, data=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('put', data=data, **kwargs)
        return requests.put(url, data=data, **kwargs, headers=headers)

    def patch(self, url, data=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('patch', data=data, **kwargs)
        return requests.patch(url, data=data, **kwargs, headers=headers)

    def delete(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('delete', **kwargs)
        return requests.delete(url, **kwargs, headers=headers)

    def request(self, method, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate(method, **kwargs)
        return requests.request(method, url, **kwargs, headers=headers)


class AppNotFound(Exception):
    pass


class AsyncService(Service):
    session: aiohttp.ClientSession

    def __init__(self, app_pk: str | int, user_pk: Optional[str | int] = None, *, mode: Optional[str] = None):
        self.app_pk = app_pk
        self.user_pk = user_pk
        self.mode = mode

    def __enter__(self) -> None:
        raise TypeError('Use async with instead')

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        pass

    async def __aenter__(self):
        from breathecode.authenticate.actions import get_app

        try:
            self.app = await sync_to_async(get_app)(self.app_pk)

        except Exception:
            raise AppNotFound(f'App {self.app_pk} not found')

        self.user_pk = self.user_pk
        self.mode = self.mode

        self.session = aiohttp.ClientSession()

        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]):
        await self.session.close()

    def aget(self, url: str, *, allow_redirects: bool = True, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        params = kwargs.pop('params', None)
        headers = self._authenticate('get', params=params, **kwargs)

        return self.session.get(url,
                                allow_redirects=allow_redirects,
                                **kwargs,
                                headers=headers,
                                params=params)

    def apost(self, url: str, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('post', data=data, **kwargs)

        return self.session.post(url, data=data, **kwargs, headers=headers)

    def awebhook(self, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        url = self.app.webhook_url
        headers = self._authenticate('post', data=data, **kwargs)

        return self.session.post(url, data=data, **kwargs, headers=headers)

    def aput(self, url: str, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('put', data=data, **kwargs)

        return self.session.put(url, data=data, **kwargs, headers=headers)

    def apatch(self, url: str, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('patch', data=data, **kwargs)

        return self.session.patch(url, data=data, **kwargs, headers=headers)

    def adelete(self, url: str, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('delete', **kwargs)

        return self.session.delete(url, **kwargs, headers=headers)

    def aoptions(self, url: str, *, allow_redirects: bool = True, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('options', **kwargs)

        return self.session.options(url, allow_redirects=allow_redirects, **kwargs, headers=headers)

    def ahead(self, url: str, *, allow_redirects: bool = True, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('head', **kwargs)

        return self.session.head(url, allow_redirects=allow_redirects, **kwargs, headers=headers)

    def arequest(self, method: str, url: str, **kwargs: Any) -> ClientResponse:
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate(method, **kwargs)

        return self.session.request(method, url, **kwargs, headers=headers)


async def service(app_pk: str | int, user_pk: Optional[str | int] = None, *, mode: Optional[str] = None):
    s = AsyncService(app_pk, user_pk, mode=mode)
    return s
