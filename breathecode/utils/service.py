from __future__ import annotations
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import hmac
import os
from typing import Optional
import jwt
import requests
import urllib.parse
from breathecode.authenticate.models import App
from breathecode.tests.mixins import DatetimeMixin

__all__ = ['get_app', 'Service']


@lru_cache(maxsize=100)
def get_app(pk: str | int) -> App:
    kwargs = {}

    if isinstance(pk, int):
        kwargs['id'] = pk

    elif isinstance(pk, str):
        kwargs['slug'] = pk

    else:
        raise Exception('Invalid pk type')

    if not (app := App.objects.filter(kwargs).first()):
        raise Exception('App not found')

    return app


class Service:

    def __init__(self, app_pk: str | int, user_pk: Optional[str | int] = None, use_signature: bool = False):
        self.app = get_app(app_pk)
        self.user_pk = user_pk
        self.use_signature = use_signature

    def _sign(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        headers = kwargs.pop('headers', {})
        headers.pop('Authorization', None)
        payload = {
            'method': method,
            'params': params,
            'data': json if json else data,
            'headers': headers,
        }

        paybytes = urllib.parse.urlencode(payload).encode('utf8')

        if self.app.algorithm == 'HMAC_SHA256':
            sign = hmac.new(self.app.private_key, paybytes, hashlib.sha256).hexdigest()

        elif self.app.algorithm == 'HMAC_SHA512':
            sign = hmac.new(self.app.private_key, paybytes, hashlib.sha512).hexdigest()

        else:
            raise Exception('Algorithm not implemented')

        headers['Authorization'] = (f'Signature App=breathecode,'
                                    f'Nonce={sign},'
                                    f'SignedHeaders={";".join(headers.keys())},'
                                    f'Date={datetime.utcnow().isoformat()}')

        return headers

    def _jwt(self, method, **kwargs) -> requests.Request:
        headers = kwargs.pop('headers', {})
        # headers.pop('Authorization', None)
        now = datetime.utcnow()

        # https://datatracker.ietf.org/doc/html/rfc7519#section-4
        payload = {
            'sub': self.user_pk,
            'iss': os.getenv('API_URL', 'http://localhost:8000'),
            'app': 'breathecode',
            'aud': self.app.slug,
            'exp': datetime.timestamp(now + timedelta(minutes=2)),
            'iat': datetime.timestamp(now),
            'typ': 'JWT',
        }

        if self.app.algorithm == 'HMAC_SHA256':
            token = jwt.encode(payload, self.app.private_key, algorithm='HS256')

        elif self.app.algorithm == 'HMAC_SHA512':
            token = jwt.encode(payload, self.app.private_key, algorithm='HS512')

        elif self.app.algorithm == 'ED25519':
            token = jwt.encode(payload, self.app.private_key, algorithm='EdDSA')

        else:
            raise Exception('Algorithm not implemented')

        headers['Authorization'] = (f'Link App=breathecode,'
                                    f'Token={token}')

        return headers

    def _authenticate(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        if self.app.strategy == 'SIGNATURE' or self.use_signature:
            return self._sign(method, params=params, data=data, json=json, **kwargs)

        elif self.app.strategy == 'JWT':
            return self._jwt(self, method, **kwargs)

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
