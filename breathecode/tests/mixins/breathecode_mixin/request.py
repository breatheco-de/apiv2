import os
from typing import Optional
from warnings import warn

import jwt
from rest_framework.test import APIClient, APITestCase

__all__ = ["Request"]


class Request:
    """Mixin with the purpose of cover all the related with the request"""

    _parent: APITestCase

    def __init__(self, parent, bc) -> None:
        self._parent = parent
        self._bc = bc

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
        warn(
            "Use rest_framework.test.APIClient instead. Example: client.get(..., headers={...})",
            DeprecationWarning,
            stacklevel=2,
        )

        headers = {}

        items = [
            index
            for index in kargs
            if kargs[index] and (isinstance(kargs[index], str) or isinstance(kargs[index], int))
        ]

        for index in items:
            headers[f"HTTP_{index.upper()}"] = str(kargs[index])

        self._parent.client.credentials(**headers)

    def authenticate(self, user) -> None:
        """
        Forces authentication in a request inside a APITestCase.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(user=1)

        # that setup the request to use the credential of user passed
        self.client.force_authenticate(model.user)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        warn("Use `client.manual_authentication` instead", DeprecationWarning, stacklevel=2)
        self._parent.client.force_authenticate(user=user)

    def manual_authentication(self, user) -> None:
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
        from breathecode.authenticate.models import Token

        warn("Use `client.credentials` instead", DeprecationWarning, stacklevel=2)

        token = Token.objects.create(user=user)
        self._parent.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def sign_jwt_link(
        self, app, user_id: Optional[int] = None, reverse: bool = False, client: Optional[APIClient] = None
    ):
        """
        Set Json Web Token in the request.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(app=1, user=1)

        # that setup the request to use the credential of user passed
        self.bc.request.authenticate(model.app, model.user.id)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        from datetime import datetime, timedelta

        from django.utils import timezone

        now = timezone.now()

        if not client:
            client = self._parent.client

        # https://datatracker.ietf.org/doc/html/rfc7519#section-4
        payload = {
            "sub": str(user_id or ""),
            "iss": os.getenv("API_URL", "http://localhost:8000"),
            "app": app.slug,
            "aud": "breathecode",
            "exp": datetime.timestamp(now + timedelta(minutes=2)),
            "iat": datetime.timestamp(now) - 1,
            "typ": "JWT",
        }

        if reverse:
            payload["aud"] = app.slug
            payload["app"] = "breathecode"

        if app.algorithm == "HMAC_SHA256":

            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS256")

        elif app.algorithm == "HMAC_SHA512":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS512")

        elif app.algorithm == "ED25519":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="EdDSA")

        else:
            raise Exception("Algorithm not implemented")

        client.credentials(HTTP_AUTHORIZATION=f"Link App={app.slug},Token={token}")
