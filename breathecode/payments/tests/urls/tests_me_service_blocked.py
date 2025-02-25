import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def get_patch(db, monkeypatch):
    yield


def test_without_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("payments:me_service_blocked")
    response = client.get(url)

    json = response.json()
    expected = {
        "detail": "Authentication credentials were not provided.",
        "status_code": 401,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_not_blocked(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_blocked")
    response = client.get(url)

    json = response.json()
    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


def test_blocked(bc: Breathecode, client: APIClient, monkeypatch: pytest.MonkeyPatch):
    slug = "dino-transformer"
    model = bc.database.create(user=1, mentorship_service={"slug": slug})
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_blocked")
    monkeypatch.setattr(
        "breathecode.payments.flags.blocked_user_ids",
        {
            "mentorship-service": {
                "from_everywhere": [1],
                "from_academy": [],
                "from_cohort": [],
                "from_mentorship_service": [],
            }
        },
    )
    response = client.get(url)

    json = response.json()
    expected = [slug]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
