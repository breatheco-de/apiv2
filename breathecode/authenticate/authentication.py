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
        token = Token.objects.select_related('user').filter(key=key).first()
        if token is None:
            raise AuthenticationFailed({'error':'Invalid or Inactive Token', 'is_authenticated': False})
 
        if not token.user.is_active:
            raise AuthenticationFailed({'error':'Invalid user', 'is_authenticated': False})
 
        now = timezone.now()
        if token.created and now < token.expires_at:
            raise AuthenticationFailed({'error':'Token has expired', 'is_authenticated': False})
        return token.user, token
