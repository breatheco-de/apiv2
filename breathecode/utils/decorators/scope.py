from datetime import timedelta
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
    from breathecode.authenticate.models import App
    from breathecode.authenticate.actions import get_app_keys

    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    if authorization.keys() != ['App', 'Token']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')

    info, key, legacy_key = get_app_keys(authorization['App'])
    app_id, alg, strategy, schema, scopes = info
    public_key, private_key = key

    for s in required_scopes:
        if s not in scopes:
            raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    if strategy != 'JWT':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    try:
        key = public_key if public_key else private_key
        payload = jwt.decode(authorization['Token'], key, algorithms=[alg])

    except:
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    try:
        legacy_public_key, legacy_private_key = legacy_key

        key = legacy_public_key if legacy_public_key else legacy_private_key
        payload = jwt.decode(authorization['Token'], key, algorithms=['HS256'])

    except:
        raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    if 'exp' not in payload or payload['exp'] < timezone.now().timestamp():
        raise ValidationException('Expired token', code=401, slug='expired')

    return app_id, payload


def get_payload(request):
    headers = request.headers
    headers.pop('Authorization', None)
    payload = {
        'body': request.body,
        'headers': headers,
        'query_params': request.query_params,
    }

    return payload


def hmac_signature(request, key, fn):
    payload = get_payload(request)

    paybytes = urllib.parse.urlencode(payload).encode('utf8')

    return hmac.new(key, paybytes, fn).hexdigest()


TOLERANCE = 2


def signature_schema(request, required_scopes, authorization: str, use_signature: bool):
    """
    Authenticate the request and return a two-tuple of (user, token).
    """
    from breathecode.authenticate.models import App
    from breathecode.authenticate.actions import get_app_keys

    try:
        authorization = dict([x.split('=') for x in authorization.split(',')])

    except:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-malformed')

    if authorization.keys() != ['App', 'Token']:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-bad-schema')

    info, key, legacy_key = get_app_keys(authorization['App'])
    app_id, alg, strategy, schema, scopes = info
    public_key, private_key = key

    for s in required_scopes:
        if s not in scopes:
            raise ValidationException('Unauthorized', code=401, slug='forbidden-scope')

    if schema != 'LINK':
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-schema')

    if strategy != 'SIGNATURE' and not use_signature:
        raise ValidationException('Unauthorized', code=401, slug='authorization-header-forbidden-strategy')

    if alg not in ['HS256', 'HS512']:
        raise ValidationException('Algorithm not implemented', code=401, slug='algorithm-not-implemented')

    fn = hashlib.sha256 if alg == 'HS256' else hashlib.sha512

    key = public_key if public_key else private_key
    if hmac_signature(request, key, fn) != authorization['Token'] and not legacy_key:
        if not legacy_key:
            raise ValidationException('Unauthorized', code=401, slug='wrong-app-token')

    legacy_public_key, legacy_private_key = legacy_key
    key = legacy_public_key if legacy_public_key else legacy_private_key
    if hmac_signature(request, key, fn) != authorization['Token']:
        raise ValidationException('Unauthorized', code=401, slug='wrong-legacy-app-token')

    try:
        timestamp = float(request.headers.get('Timestamp', ''))
        if ((timezone.now() - timedelta(minutes=TOLERANCE)).timestamp() < timestamp <
            (timezone.now() + timedelta(minutes=TOLERANCE)).timestamp()):
            raise Exception()

    except:
        raise ValidationException('Unauthorized', code=401, slug='bad-timestamp')

    return app_id


def scope(scopes: list = [], use_signature: bool = False) -> callable:
    """This decorator check if the app has access to the scope provided"""

    from breathecode.authenticate.models import App

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
                authorization = authorization.replace('Link ', '')
                app_id, token = link_schema(request, scopes, authorization, use_signature)
                function(*args, **kwargs, token=token, app_id=app_id)

            elif authorization.startswith('Signature '):
                authorization = authorization.replace('Signature ', '')
                app_id = signature_schema(request, scopes, authorization, use_signature)
                function(*args, **kwargs, app_id=app_id)

            else:
                raise ValidationException('Unknown auth schema or this schema is forbidden',
                                          code=401,
                                          slug='unknown-auth-schema')

        return wrapper

    return decorator
