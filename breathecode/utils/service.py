from __future__ import annotations
from typing import Optional
import requests

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

    def get(self, url, params=None, **kwargs):
        headers = self._authenticate('get', params=params, **kwargs)
        return requests.get(url, params=params, **kwargs, headers=headers)

    def options(self, url, **kwargs):
        headers = self._authenticate('options', **kwargs)
        return requests.options(url, **kwargs, headers=headers)

    def head(self, url, **kwargs):
        headers = self._authenticate('head', **kwargs)
        return requests.head(url, **kwargs, headers=headers)

    def post(self, url, data=None, json=None, **kwargs):
        headers = self._authenticate('post', data=data, json=json, **kwargs)
        return requests.post(url, data=data, json=json, **kwargs, headers=headers)

    def put(self, url, data=None, **kwargs):
        headers = self._authenticate('put', data=data, **kwargs)
        return requests.put(url, data=data, **kwargs, headers=headers)

    def patch(self, url, data=None, **kwargs):
        headers = self._authenticate('patch', data=data, **kwargs)
        return requests.patch(url, data=data, **kwargs, headers=headers)

    def delete(self, url, **kwargs):
        headers = self._authenticate('delete', **kwargs)
        return requests.delete(url, **kwargs, headers=headers)

    def request(self, method, url, **kwargs):
        headers = self._authenticate(method, **kwargs)
        return requests.request(method, url, **kwargs, headers=headers)
