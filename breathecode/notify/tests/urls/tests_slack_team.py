"""
Test /slack/team
"""

import json

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


def get_serializer(team, data={}):
    return {
        "id": team.id,
        "slack_id": team.slack_id,
        "name": team.name,
        "academy": {
            "id": team.academy.id,
            "name": team.academy.name,
            "slug": team.academy.slug,
        },
        "created_at": team.created_at,
        "sync_message": team.sync_message,
        "sync_status": team.sync_status,
        **data,
    }


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("notify:slack_team")
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("notify.SlackTeam") == []


def test_no_teams(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:slack_team")
    response = client.get(url)

    json = response.json()
    expected = []
    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("notify.SlackTeam") == []


def test_with_teams(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, slack_team=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:slack_team")
    response = client.get(url)

    json = response.json()
    expected = [
        get_serializer(model.slack_team, data={"created_at": bc.datetime.to_iso_string(model.slack_team.created_at)})
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("notify.SlackTeam") == [bc.format.to_dict(model.slack_team)]


def test_with_teams_filtering(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, academy={"slug": "hogwartz"}, slack_team=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:slack_team") + "?academy=hogwartz"
    response = client.get(url)

    json = response.json()
    expected = [
        get_serializer(model.slack_team, data={"created_at": bc.datetime.to_iso_string(model.slack_team.created_at)})
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("notify.SlackTeam") == [bc.format.to_dict(model.slack_team)]


def test_with_teams_filtering_no_academy(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, academy={"slug": "hogwartz"}, slack_team=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:slack_team") + "?academy=adasdasd"
    response = client.get(url)

    json = response.json()
    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("notify.SlackTeam") == [bc.format.to_dict(model.slack_team)]
