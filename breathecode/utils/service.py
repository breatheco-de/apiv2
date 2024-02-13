from __future__ import annotations

from types import TracebackType
from typing import Any, Coroutine, Optional, Type

import aiohttp
import requests
from aiohttp.client_reqrep import ClientResponse
from asgiref.sync import sync_to_async
from django.core.exceptions import SynchronousOnlyOperation
from django.http import HttpResponse, StreamingHttpResponse

__all__ = ['Service']


class Service:
    session: aiohttp.ClientSession

    def __init__(self,
                 app_pk: str | int,
                 user_pk: Optional[str | int] = None,
                 *,
                 mode: Optional[str] = None,
                 proxy: bool = False):
        self.app_pk = app_pk
        self.user_pk = user_pk
        self.mode = mode
        self.to_close = []
        self.proxy = proxy
        self.banned_keys = [
            'Transfer-Encoding', 'Content-Encoding', 'Keep-Alive', 'Connection', 'Content-Length', 'Upgrade'
        ]

    def __enter__(self) -> 'Service':
        from breathecode.authenticate.actions import get_app
        from breathecode.authenticate.models import App
        from breathecode.utils import ValidationException

        self.sync = True

        if isinstance(self.app_pk, App):
            self.app = self.app_pk
            return self

        try:
            self.app = get_app(self.app_pk)

        except Exception:
            if self.proxy:
                raise ValidationException(f'App {self.app_pk} not found', code=404, slug='app-not-found')

            raise AppNotFound(f'App {self.app_pk} not found')

        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        pass

    async def __aenter__(self) -> 'Service':
        from breathecode.authenticate.actions import get_app
        from breathecode.authenticate.models import App
        from breathecode.utils import ValidationException

        self.sync = False

        if isinstance(self.app_pk, App):
            self.app = self.app_pk

        else:
            try:
                self.app = await sync_to_async(get_app)(self.app_pk)

            except SynchronousOnlyOperation as e:
                if self.proxy:
                    raise ValidationException('Async is not supported by the worker',
                                              code=500,
                                              slug='no-async-support')

                raise e

            except Exception:
                if self.proxy:
                    raise ValidationException(f'App {self.app_pk} not found', code=404, slug='app-not-found')

                raise AppNotFound(f'App {self.app_pk} not found')

        self.session = aiohttp.ClientSession()

        # this should be extended
        await self.session.__aenter__()

        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]):
        for obj in self.to_close:
            await obj.__aexit__()

        await self.session.__aexit__()

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

    def _proxy(self, response: requests.Response, stream: bool) -> StreamingHttpResponse:
        header_keys = [x for x in response.headers.keys() if x not in self.banned_keys]

        if stream:
            resource = StreamingHttpResponse(
                response.raw,
                status=response.status_code,
                reason=response.reason,
            )

            for header in header_keys:
                resource[header] = response.headers[header]

            return resource

        headers = {}

        for header in header_keys:
            headers[header] = response.headers[header]

        return HttpResponse(response.content, status=response.status_code, headers=headers)

    # django does not support StreamingHttpResponse with aiohttp due to django would have to close the response
    async def _aproxy(self, response: Coroutine[Any, Any, ClientResponse]) -> HttpResponse:
        r = await response

        header_keys = [x for x in r.headers.keys() if x not in self.banned_keys]

        headers = {}
        for header in header_keys:
            headers[str(header)] = r.headers[header]

        return HttpResponse(await r.content.read(), status=r.status, headers=headers)

    def get(self, url, params=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)

        if self.sync is False:
            params = kwargs.pop('params', None)

        headers = self._authenticate('get', params=params, **kwargs)

        if self.sync:
            res = requests.get(url, params=params, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.get(url, params=params, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def options(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('options', **kwargs)

        if self.sync:
            res = requests.options(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.options(url, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def head(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('head', **kwargs)

        if self.sync:
            res = requests.head(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.head(url, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def post(self, url, data=None, json=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('post', data=data, json=json, **kwargs)

        if self.sync:
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def webhook(self, url, data=None, json=None, **kwargs):
        url = self.app.webhook_url
        headers = self._authenticate('post', data=data, json=json, **kwargs)

        if self.sync:
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def put(self, url, data=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('put', data=data, **kwargs)

        if self.sync:
            res = requests.put(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.put(url, data=data, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def patch(self, url, data=None, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('patch', data=data, **kwargs)

        if self.sync:
            res = requests.patch(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.patch(url, data=data, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def delete(self, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate('delete', **kwargs)

        if self.sync:
            res = requests.delete(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.delete(url, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res

    def request(self, method, url, **kwargs):
        url = self.app.app_url + self._fix_url(url)
        headers = self._authenticate(method, **kwargs)

        if self.sync:
            res = requests.request(method, url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get('stream', False))

            return res

        obj = self.session.request(method, url, **kwargs, headers=headers)
        self.to_close.append(obj)

        res = obj.__aenter__()

        # wraps client response to be used within django views
        if self.proxy:
            return self._aproxy(res)

        return res


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
        for obj in self.to_close:
            await obj.__aexit__()

        await self.session.__aexit__()

    def awebhook(self, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        url = self.app.webhook_url
        headers = self._authenticate('post', data=data, **kwargs)

        return self.session.post(url, data=data, **kwargs, headers=headers)
