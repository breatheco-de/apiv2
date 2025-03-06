"""
Test /academy/settings/log
"""

import pytest
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def test_not_authenticated(bc: Breathecode, client: APIClient):

    url = reverse_lazy("authenticate:academy_settings_log")

    response = client.get(url, headers={"academy": 1})

    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
    json = response.json()

    assert json == expected
    assert response.status_code == 401


def test_no_capability(bc: Breathecode, client: APIClient):

    url = reverse_lazy("authenticate:academy_settings_log")
    model = bc.database.create(user=1)

    client.force_authenticate(model.user)

    response = client.get(url, headers={"academy": 1})

    expected = {
        "detail": "You (user: 1) don't have this capability: get_academy_auth_settings for academy 1",
        "status_code": 403,
    }
    json = response.json()

    assert json == expected
    assert response.status_code == 403


def test_settings_not_found(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1,
        role=1,
        capability="get_academy_auth_settings",
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:academy_settings_log")
    response = client.get(url, headers={"academy": 1})

    expected = {"detail": "no-github-auth-settings", "status_code": 400}
    json = response.json()

    assert expected == json
    assert response.status_code == 400


def test_settings_no_log(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1, role=1, capability="get_academy_auth_settings", academy_auth_settings=1
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:academy_settings_log")
    response = client.get(url, headers={"academy": 1})

    expected = []
    json = response.json()

    assert expected == json
    assert response.status_code == 200


def test_settings_with_log(bc: Breathecode, client: APIClient):

    log = [
        {
            "at": "2025-01-28 02:02:41.228000+00:00",
            "msg": "Error inviting member lord@valdomero.com to org: Unable to communicate with Github API",
        },
        {
            "at": "2025-01-28 12:35:14.857450+00:00",
            "msg": "Error inviting member lord@valdomero.com to org: Unable to communicate with Github API",
        },
    ]

    model = bc.database.create(
        profile_academy=1,
        role=1,
        capability="get_academy_auth_settings",
        academy_auth_settings={"github_error_log": log},
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:academy_settings_log")
    response = client.get(url, headers={"academy": 1})

    expected = log
    json = response.json()

    assert expected == json
    assert response.status_code == 200
