from rest_framework.test import APITestCase

from breathecode.authenticate.models import Token, User

__all__ = ['Request']


class Request:
    """Mixin with the purpose of cover all the related with the request"""

    _parent: APITestCase

    def set_headers(self, **kargs: str) -> None:
        """
        Set headers.

        ```py
        # It set the headers with:
        #   Academy: 1
        #   ThingOfImportance: potato
        self.bc.request.set_headers(academy=1, thing_of_importance='potato')
        ```
        """
        headers = {}

        items = [
            index for index in kargs
            if kargs[index] and (isinstance(kargs[index], str) or isinstance(kargs[index], int))
        ]

        for index in items:
            headers[f'HTTP_{index.upper()}'] = str(kargs[index])

        self._parent.client.credentials(**headers)

    def __init__(self, parent) -> None:
        self._parent = parent

    def authenticate(self, user: User) -> None:
        """
        Forces authentication in a request inside a APITestCase.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(user=1)

        # that setup the request to use the credential of user passed
        self.bc.request.authenticate(model.user)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        self._parent.client.force_authenticate(user=user)

    def manual_authentication(self, user: User) -> None:
        """
        Generate a manual authentication using a token, this method is more slower than `authenticate`.

        ```py
        # setup the database
        model = self.bc.database.create(user=1)

        # that setup the request to use the credential with tokens of user passed
        self.bc.request.manual_authentication(model.user)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`.
        """
        token = Token.objects.create(user=user)
        self._parent.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
