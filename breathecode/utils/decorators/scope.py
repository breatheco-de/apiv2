from datetime import datetime, timedelta
import hashlib
import hmac
import logging

from django.utils import timezone
import jwt
from rest_framework.views import APIView
import urllib.parse

from ..exceptions import ProgrammingError
from ..validation_exception import ValidationException

__all__ = ['scope']

logger = logging.getLogger(__name__)


def link_schema(request, required_scopes, authorization: str, use_signature: bool):
    """
    Authenticate the request and return a two-tuple of (user, token).
    """
    from breathecode.authenticate.actions import get_app_keys, get_user_scopes

    print('here 0')
    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    print('here 1', authorization.keys(), sorted(authorization.keys()) == ['App', 'Token'])
    if sorted(authorization.keys()) != ['App', 'Token']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')
    print('here 1')

    info, key, legacy_key = get_app_keys(authorization['App'])
    app_id, alg, strategy, schema, require_an_agreement, required_app_scopes, optional_app_scopes = info
    public_key, private_key = key

    print('here 2')

    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    if strategy != 'JWT':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    print('here 3')
    try:
        key = public_key if public_key else private_key
        payload = jwt.decode(authorization['Token'], key, algorithms=[alg], audience='breathecode')

    except Exception as e:
        print(1, e)
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    print('here 4')

    if not payload:
        try:
            legacy_public_key, legacy_private_key = legacy_key

            key = legacy_public_key if legacy_public_key else legacy_private_key
            payload = jwt.decode(authorization['Token'], key, algorithms=[alg])

        except Exception as e:
            print(2, e)
            raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    print('here 5')
    if require_an_agreement:
        required_app_scopes, optional_app_scopes = get_user_scopes(authorization['App'], payload['sub'])
        all_scopes = required_app_scopes + optional_app_scopes

        for s in required_scopes:
            if s not in all_scopes:
                raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    print('here 6')
    if 'exp' not in payload or payload['exp'] < timezone.now().timestamp():
        raise ValidationException('Expired token', code=401, slug='expired')

    print('here 7')
    return app_id, payload


def get_payload(app, date, signed_headers, request):
    headers = dict(request.headers)
    headers.pop('Authorization', None)
    payload = {
        'timestamp': date,
        'app': app,
        'method': request.method,
        'params': dict(request.GET),
        'body': request.data if request.data is not None else None,
        'headers': {k: v
                    for k, v in headers.items() if k in signed_headers},
    }
    print(222, payload)

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
    from breathecode.authenticate.models import App
    from breathecode.authenticate.actions import get_app_keys, get_user_scopes

    print(1)
    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    print(2)
    if sorted(authorization.keys()) != ['App', 'Date', 'Nonce', 'SignedHeaders']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')

    print(3)
    info, key, legacy_key = get_app_keys(authorization['App'])
    app_id, alg, strategy, schema, require_an_agreement, required_app_scopes, optional_app_scopes = info
    public_key, private_key = key

    if require_an_agreement:
        required_app_scopes, optional_app_scopes = get_user_scopes(authorization['App'], payload['sub'])
        all_scopes = required_app_scopes + optional_app_scopes

        for s in required_scopes:
            if s not in all_scopes:
                raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    print(4)
    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    print(5)
    if strategy != 'SIGNATURE' and not use_signature:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    print(6)
    if alg not in ['HS256', 'HS512']:
        raise ValidationException('Algorithm not implemented', code=401, slug='algorithm-not-implemented')

    fn = hashlib.sha256 if alg == 'HS256' else hashlib.sha512

    print(7)
    key = public_key if public_key else private_key
    if hmac_signature(authorization['App'], authorization['Date'], authorization['SignedHeaders'], request,
                      key, fn) != authorization['Nonce'] and not legacy_key:
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    print(8)
    if legacy_key:
        legacy_public_key, legacy_private_key = legacy_key
        key = legacy_public_key if legacy_public_key else legacy_private_key
        if hmac_signature(authorization['App'], authorization['Date'], authorization['SignedHeaders'],
                          request, key, fn) != authorization['Nonce']:
            raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    print(9)
    try:
        date = datetime.fromisoformat(authorization['Date'])
        date = date.replace(tzinfo=timezone.utc)
        now = timezone.now()
        print(date, now)
        if (now - timedelta(minutes=TOLERANCE) > date) or (now + timedelta(minutes=TOLERANCE) < date):
            raise Exception()

    except Exception as e:
        print(33333, e)
        raise ValidationException('Unauthorized', code=401, slug='bad-timestamp')

    print(10)
    return app_id


def scope(scopes: list = [], use_signature: bool = False) -> callable:
    """This decorator check if the app has access to the scope provided"""

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

            if authorization.startswith('Link ') and not use_signature:
                print('-1')
                authorization = authorization.replace('Link ', '')
                app_id, token = link_schema(request, scopes, authorization, use_signature)
                return function(*args, **kwargs, token=token, app_id=app_id)

            elif authorization.startswith('Signature '):
                print('-2')
                authorization = authorization.replace('Signature ', '')
                app_id = signature_schema(request, scopes, authorization, use_signature)
                return function(*args, **kwargs, app_id=app_id)

            else:
                print('-3')
                raise ValidationException('Unknown auth schema or this schema is forbidden',
                                          code=401,
                                          slug='unknown-auth-schema')

        return wrapper

    return decorator
