# authentication.py

from rest_framework.authentication import TokenAuthentication
from .models import Token
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone


class ExpiringTokenAuthentication(TokenAuthentication):
    '''
    Expiring token for mobile and desktop clients.
    It expires every 24hrs requiring client to supply valid username
    and password for new one to be created.
    '''
    def authenticate_credentials(self, key, request=None):
        print('request', request)
        print('key', key)
        x = Token.objects.filter(key=key).first()
        if x:
            print('token data', vars(Token.objects.filter(key=key).first()))
        else:
            print('token not found')
        token = Token.objects.select_related('user').filter(key=key).first()
        print('token', token)
        if token is None:
            raise AuthenticationFailed({'error': 'Invalid or Inactive Token', 'is_authenticated': False})

        print('after Invalid or Inactive Token')
        print('user is active', token.user.is_active)
        if not token.user.is_active:
            raise AuthenticationFailed({'error': 'Invalid or inactive user', 'is_authenticated': False})

        now = timezone.now()
        if token.expires_at is not None and token.expires_at < now:
            raise AuthenticationFailed({
                'error': 'Token expired at ' + str(token.expires_at),
                'is_authenticated': False
            })
        return token.user, token
