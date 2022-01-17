from rest_framework.test import APITestCase

from breathecode.authenticate.models import Token, User
from ..headers_mixin import HeadersMixin

__all__ = ['Request']


class Request:
    """Wrapper of last implementation for request for testing purposes"""

    set_headers = HeadersMixin.headers
    parent: APITestCase

    def __init__(self, parent) -> None:
        self.parent = parent

    def authenticate(self, user: User) -> None:
        """
        Forces authentication in a request inside a APITestCase

        Keywords arguments:
        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        self.parent.client.force_authenticate(user=user)

    def manual_authentication(self, user: User) -> None:
        """
        Generate a manual authentication using a token, this method is more slower than `authenticate`

        Keywords arguments:
        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        token = Token.objects.create(user=user)
        self.parent.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
