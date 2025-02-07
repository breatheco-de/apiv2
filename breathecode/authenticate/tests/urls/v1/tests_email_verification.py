"""
Test cases for /emailvalidation
"""

import pytest
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def test_email_verification_no_user(bc: Breathecode, client: APIClient):
    email = "thanos@4geeks.com"

    url = reverse_lazy("authenticate:email_verification", kwargs={"email": email})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "email-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_email_verification_not_validated(bc: Breathecode, client: APIClient):
    email = "thanos@4geeks.com"

    model = bc.database.create(user={"email": email}, user_invite={"email": email, "is_email_validated": False})

    url = reverse_lazy("authenticate:email_verification", kwargs={"email": email})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "email-not-validated", "status_code": 403}

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_email_verification(bc: Breathecode, client: APIClient):
    email = "thanos@4geeks.com"
    model = bc.database.create(user={"email": email})

    url = reverse_lazy("authenticate:email_verification", kwargs={"email": email})
    response = client.get(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
