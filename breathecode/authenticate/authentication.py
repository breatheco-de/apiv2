# authentication.py

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

HTTP_HEADER_ENCODING = "iso-8859-1"


def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get("HTTP_AUTHORIZATION", b"")
    if isinstance(auth, str):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Expiring token for mobile and desktop clients.

    It expires every 24hrs requiring client to supply valid username
    and password for new one to be created.
    """

    def authenticate_credentials(self, key, request=None):
        from .models import Token

        token = Token.objects.select_related("user").filter(key=key).first()
        if token is None:
            raise AuthenticationFailed({"error": "Invalid or Inactive Token", "is_authenticated": False})

        if not token.user.is_active:
            raise AuthenticationFailed({"error": "Invalid or inactive user", "is_authenticated": False})

        now = timezone.now()
        if token.expires_at is not None and token.expires_at < now:
            raise AuthenticationFailed(
                {"error": "Token expired at " + str(token.expires_at), "is_authenticated": False}
            )
        return token.user, token


class AsyncExpiringTokenAuthentication(ExpiringTokenAuthentication):
    """
    Expiring token for mobile and desktop clients.

    It expires every 24hrs requiring client to supply valid username
    and password for new one to be created.
    """

    async def authenticate(self, request):

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _("Invalid token header. Token string should not contain invalid characters.")
            raise AuthenticationFailed(msg)

        return await sync_to_async(self.authenticate_credentials)(token)
