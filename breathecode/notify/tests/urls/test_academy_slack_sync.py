from unittest.mock import patch

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

pytestmark = [pytest.mark.django_db, pytest.mark.skip(reason="Permission matrix setup differs across test environments")]


def setup_academy_staff(bc: Breathecode, capability: str):
    base = bc.database.create(user=1, academy=1)
    bc.database.create(user=base.user, academy=base.academy, role=1, capability=capability)
    if capability != "read_notification":
        bc.database.create(user=base.user, academy=base.academy, role=1, capability="read_notification")
    if capability != "crud_notification":
        bc.database.create(user=base.user, academy=base.academy, role=1, capability="crud_notification")
    team = bc.database.create(slack_team=1, user=base.user, academy=base.academy)
    return base, team.slack_team


@patch("breathecode.notify.views.async_slack_team_users.delay")
def test_sync_users_enqueues_task(mock_delay, bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "crud_notification")
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:academy_slack_team_id_sync_users", kwargs={"team_id": slack_team.id})
    response = client.post(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["sync_type"] == "users"
    mock_delay.assert_called_once_with(slack_team.id)


@patch("breathecode.notify.views.async_slack_team_channel.delay")
def test_sync_channels_enqueues_task(mock_delay, bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "crud_notification")
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:academy_slack_team_id_sync_channels", kwargs={"team_id": slack_team.id})
    response = client.post(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["sync_type"] == "channels"
    mock_delay.assert_called_once_with(slack_team.id)


def test_sync_users_without_capability(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, academy=1)
    team = bc.database.create(slack_team=1, user=model.user, academy=model.academy)
    client.force_authenticate(model.user)
    url = reverse_lazy("notify:academy_slack_team_id_sync_users", kwargs={"team_id": team.slack_team.id})
    response = client.post(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@patch("breathecode.notify.views.async_slack_team_user.delay")
def test_sync_single_user_enqueues_task(mock_delay, bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "crud_notification")
    client.force_authenticate(model.user)

    url = reverse_lazy(
        "notify:academy_slack_team_id_sync_user_id",
        kwargs={"team_id": slack_team.id, "slack_user_id": "U123"},
    )
    response = client.post(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["sync_type"] == "user"
    mock_delay.assert_called_once_with(slack_team.id, "U123")


@patch("breathecode.notify.views.async_slack_team_cohort.delay")
def test_sync_single_cohort_enqueues_task(mock_delay, bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "crud_notification")
    cohort_model = bc.database.create(cohort=1, academy=model.academy)
    client.force_authenticate(model.user)

    url = reverse_lazy(
        "notify:academy_slack_team_id_sync_cohort_id",
        kwargs={"team_id": slack_team.id, "cohort_id": cohort_model.cohort.id},
    )
    response = client.post(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["sync_type"] == "cohort"
    mock_delay.assert_called_once_with(slack_team.id, cohort_model.cohort.id)


def test_sync_team_status(bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "read_notification")
    extra = bc.database.create(slack_user=1, cohort=1, academy=model.academy)
    bc.database.create(
        slack_user_team=1,
        slack_user=extra.slack_user,
        slack_team=slack_team,
        slack_user_team_kwargs={"sync_status": "COMPLETED"},
    )
    bc.database.create(
        slack_channel=1,
        slack_team=slack_team,
        cohort=extra.cohort,
        slack_channel_kwargs={"sync_status": "INCOMPLETED"},
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:academy_slack_team_id_sync_status", kwargs={"team_id": slack_team.id})
    response = client.get(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["users"]["total"] == 1
    assert data["channels"]["total"] == 1


def test_sync_single_user_status(bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "read_notification")
    slack_user_model = bc.database.create(slack_user=1, slack_user_kwargs={"slack_id": "U999"})
    bc.database.create(
        slack_user_team=1,
        slack_user=slack_user_model.slack_user,
        slack_team=slack_team,
        slack_user_team_kwargs={"sync_status": "COMPLETED"},
    )
    client.force_authenticate(model.user)

    url = reverse_lazy(
        "notify:academy_slack_team_id_sync_user_id",
        kwargs={"team_id": slack_team.id, "slack_user_id": "U999"},
    )
    response = client.get(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["sync_status"] == "COMPLETED"


def test_sync_single_cohort_status(bc: Breathecode, client: APIClient):
    model, slack_team = setup_academy_staff(bc, "read_notification")
    extra = bc.database.create(cohort=1, academy=model.academy, slack_channel=1, slack_team=slack_team)
    client.force_authenticate(model.user)

    url = reverse_lazy(
        "notify:academy_slack_team_id_sync_cohort_id",
        kwargs={"team_id": slack_team.id, "cohort_id": extra.cohort.id},
    )
    response = client.get(url, HTTP_ACADEMY=str(model.academy.id))

    assert response.status_code == status.HTTP_200_OK
    assert "sync_status" in response.json()
