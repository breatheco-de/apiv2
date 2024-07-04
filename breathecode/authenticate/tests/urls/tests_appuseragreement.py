"""
Test cases for /user
"""

import random
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import fake

from ..mixins.new_auth_test_case import AuthTestCase

UTC_NOW = timezone.now()
TOKEN = fake.name()


def get_serializer(app, data={}):
    return {
        "app": app.slug,
        "up_to_date": True,
        **data,
    }


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    # When: no auth
    # Then: return 401
    def test__auth__without_auth(self):
        """Test /logout without auth"""
        url = reverse_lazy("authenticate:appuseragreement")

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("linked_services.AppUserAgreement"), [])

    # When: no agreements
    # Then: return empty list
    def test__no_agreements(self):
        url = reverse_lazy("authenticate:appuseragreement")

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("linked_services.AppUserAgreement"), [])

        # teardown
        self.bc.database.delete("authenticate.Token")

    # When: have agreements, agreement_version match
    # Then: return list of agreements
    def test__have_agreements__version_match(self):
        url = reverse_lazy("authenticate:appuseragreement")

        version = random.randint(1, 100)
        app = {"agreement_version": version}
        app_user_agreements = [{"agreement_version": version, "app_id": x + 1} for x in range(2)]
        model = self.bc.database.create(user=1, app=(2, app), app_user_agreement=app_user_agreements)
        self.client.force_authenticate(model.user)
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(model.app[0], {"up_to_date": True}),
            get_serializer(model.app[1], {"up_to_date": True}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("linked_services.AppUserAgreement"),
            self.bc.format.to_dict(model.app_user_agreement),
        )

    # When: have agreements, agreement_version match
    # Then: return list of agreements
    def test__have_agreements__version_does_not_match(self):
        url = reverse_lazy("authenticate:appuseragreement")

        version1 = random.randint(1, 100)
        version2 = random.randint(1, 100)
        while version1 == version2:
            version2 = random.randint(1, 100)
        app = {"agreement_version": version1}
        app_user_agreements = [{"agreement_version": version2, "app_id": x + 1} for x in range(2)]
        model = self.bc.database.create(user=1, app=(2, app), app_user_agreement=app_user_agreements)
        self.client.force_authenticate(model.user)
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(model.app[0], {"up_to_date": False}),
            get_serializer(model.app[1], {"up_to_date": False}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("linked_services.AppUserAgreement"),
            self.bc.format.to_dict(model.app_user_agreement),
        )
