import datetime as dt
from datetime import datetime, timedelta
import hashlib
import hmac
import logging
from typing import Optional

from django.utils import timezone
import jwt
from rest_framework.views import APIView
import urllib.parse

from breathecode.utils.attr_dict import AttrDict

from ..exceptions import ProgrammingError
from ..validation_exception import ValidationException

__all__ = ['scope']

logger = logging.getLogger(__name__)


def link_schema(request, required_scopes, authorization: str, use_signature: bool):
    """
    Authenticate the request and return a two-tuple of (user, token).
    """
    from breathecode.authenticate.actions import get_app_keys, get_user_scopes

    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except Exception:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    if sorted(authorization.keys()) != ['App', 'Token']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')

    info, key, legacy_key = get_app_keys(authorization['App'])
    (app_id, alg, strategy, schema, require_an_agreement, required_app_scopes, optional_app_scopes,
     webhook_url, redirect_url, app_url) = info
    public_key, private_key = key

    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    if strategy != 'JWT':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    try:
        key = public_key if public_key else private_key
        payload = jwt.decode(authorization['Token'], key, algorithms=[alg], audience='4geeks')

    except Exception:
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    if not payload:
        try:
            legacy_public_key, legacy_private_key = legacy_key

            key = legacy_public_key if legacy_public_key else legacy_private_key
            payload = jwt.decode(authorization['Token'], key, algorithms=[alg])

        except Exception:
            raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    if payload['sub'] and require_an_agreement:
        required_app_scopes, optional_app_scopes = get_user_scopes(authorization['App'], payload['sub'])
        all_scopes = required_app_scopes + optional_app_scopes

        for s in required_scopes:
            if s not in all_scopes:
                raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    if 'exp' not in payload or payload['exp'] < timezone.now().timestamp():
        raise ValidationException('Expired token', code=401, slug='expired')

    app = {
        'id': app_id,
        'private_key': private_key,
        'public_key': public_key,
        'algorithm': alg,
        'strategy': strategy,
        'schema': schema,
        'require_an_agreement': require_an_agreement,
        'webhook_url': webhook_url,
        'redirect_url': redirect_url,
        'app_url': app_url,
    }

    return app, payload


def get_payload(app, date, signed_headers, request):
    headers = dict(request.headers)
    headers.pop('Authorization', None)
    payload = {
        'timestamp': date,
        'app': app,
        'method': request.method,
        'params': dict(request.GET),
        'body': request.data if request.data is not None else None,
        'headers': {
            k: v
            for k, v in headers.items() if k in signed_headers
        },
    }

    return payload


def hmac_signature(app, date, signed_headers, request, key, fn):
    payload = get_payload(app, date, signed_headers, request)

    paybytes = urllib.parse.urlencode(payload).encode('utf8')

    return hmac.new(key, paybytes, fn).hexdigest()


TOLERANCE = 2


def signature_schema(request, required_scopes, authorization: str, use_signature: bool):
    """
    Authenticate the request and return a two-tuple of (user, token).
    """
    from breathecode.authenticate.actions import get_app_keys, get_user_scopes

    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except Exception:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    if sorted(authorization.keys()) != ['App', 'Date', 'Nonce', 'SignedHeaders']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')

    info, key, legacy_key = get_app_keys(authorization['App'])
    (app_id, alg, strategy, schema, require_an_agreement, required_app_scopes, optional_app_scopes,
     webhook_url, redirect_url, app_url) = info
    public_key, private_key = key

    if require_an_agreement:
        required_app_scopes, optional_app_scopes = get_user_scopes(authorization['App'])
        all_scopes = required_app_scopes + optional_app_scopes

        for s in required_scopes:
            if s not in all_scopes:
                raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    if strategy != 'SIGNATURE' and not use_signature:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    if alg not in ['HS256', 'HS512']:
        raise ValidationException('Algorithm not implemented', code=401, slug='algorithm-not-implemented')

    fn = hashlib.sha256 if alg == 'HS256' else hashlib.sha512

    key = public_key if public_key else private_key
    if hmac_signature(authorization['App'], authorization['Date'], authorization['SignedHeaders'], request,
                      key, fn) != authorization['Nonce'] and not legacy_key:
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    if legacy_key:
        legacy_public_key, legacy_private_key = legacy_key
        key = legacy_public_key if legacy_public_key else legacy_private_key
        if hmac_signature(authorization['App'], authorization['Date'], authorization['SignedHeaders'],
                          request, key, fn) != authorization['Nonce']:
            raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    try:
        date = datetime.fromisoformat(authorization['Date'])
        date = date.replace(tzinfo=dt.timezone.utc)
        now = timezone.now()
        if (now - timedelta(minutes=TOLERANCE) > date) or (now + timedelta(minutes=TOLERANCE) < date):
            raise Exception()

    except Exception:
        raise ValidationException('Unauthorized', code=401, slug='bad-timestamp')

    app = {
        'id': app_id,
        'private_key': private_key,
        'public_key': public_key,
        'algorithm': alg,
        'strategy': strategy,
        'schema': schema,
        'require_an_agreement': require_an_agreement,
        'webhook_url': webhook_url,
        'redirect_url': redirect_url,
        'app_url': app_url,
    }

    return app


def scope(scopes: Optional[list] = None, mode: Optional[str] = None) -> callable:
    """This decorator check if the app has access to the scope provided"""

    if scopes is None:
        scopes = []

    def decorator(function: callable) -> callable:

        def wrapper(*args, **kwargs):

            if isinstance(scopes, list) == False:
                raise ProgrammingError('Permission must be a list')

            if len([x for x in scopes if not isinstance(x, str)]):
                raise ProgrammingError('Permission must be a list of strings')

            try:
                if hasattr(args[0], '__class__') and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], 'user'):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError('Missing request information, use this decorator with DRF View')

            authorization = request.headers.get('Authorization', '')
            if not authorization:
                raise ValidationException('Unauthorized', code=401, slug='no-authorization-header')

            if authorization.startswith('Link ') and mode != 'signature':
                authorization = authorization.replace('Link ', '')
                app, token = link_schema(request, scopes, authorization, mode == 'signature')
                return function(*args, **kwargs, token=AttrDict(**token), app=AttrDict(**app))

            elif authorization.startswith('Signature ') and mode != 'jwt':
                authorization = authorization.replace('Signature ', '')
                app = signature_schema(request, scopes, authorization, mode == 'signature')
                return function(*args, **kwargs, app=AttrDict(**app))

            else:
                raise ValidationException('Unknown auth schema or this schema is forbidden',
                                          code=401,
                                          slug='unknown-auth-schema')

        return wrapper

    return decorator
