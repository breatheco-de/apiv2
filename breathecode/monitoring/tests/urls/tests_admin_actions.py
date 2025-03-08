from unittest.mock import MagicMock, call

import pytest
from capyc import pytest as capy
from django.contrib.admin import site
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.admissions.admin import CohortAdmin, CohortUserAdmin
from breathecode.admissions.models import Cohort, CohortUser


@pytest.fixture(autouse=True)
def action_mock(monkeypatch: pytest.MonkeyPatch):

    monkeypatch.setattr(
        site,
        "_registry",
        {CohortUser: CohortUserAdmin(Cohort, site), Cohort: CohortAdmin(Cohort, site)},
    )


def tests_no_auth(client: capy.Client):
    url = reverse_lazy("monitoring:admin_actions")
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def tests_no_admin(client: capy.Client, database: capy.Database):
    model = database.create(user={"is_staff": False})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    response = client.get(url)

    json = response.json()
    expected = {"detail": "You do not have permission to perform this action.", "status_code": 403}

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN


def tests_get(client: capy.Client, database: capy.Database):
    model = database.create(user={"is_staff": True})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    response = client.get(url)

    json = response.json()
    expected = {
        "breathecode.admissions.admin.CohortAdmin": {
            "actions": [
                "sync_tasks",
                "mark_as_ended",
                "mark_as_started",
                "mark_as_inactive",
                "sync_timeslots",
                "add_cohort_slug_to_active_campaign",
                "get_attendancy_logs",
            ],
            "model": "breathecode.admissions.models.Cohort",
            "model_admin": "breathecode.admissions.admin.CohortAdmin",
            "properties": {
                "list_display": [
                    "id",
                    "slug",
                    "stage",
                    "name",
                    "kickoff_date",
                    "syllabus_version",
                    "schedule",
                    "academy",
                ],
                "list_filter": [
                    "stage",
                    "academy__slug",
                    "schedule__name",
                    "syllabus_version__version",
                ],
                "search_fields": [
                    "slug",
                    "name",
                    "academy__city__name",
                ],
            },
        },
        "breathecode.admissions.admin.CohortUserAdmin": {
            "actions": [
                "make_assistant",
                "make_teacher",
                "make_student",
                "make_edu_stat_active",
                "add_student_tag_to_active_campaign",
            ],
            "model": "breathecode.admissions.models.CohortUser",
            "model_admin": "breathecode.admissions.admin.CohortUserAdmin",
            "properties": {
                "list_display": [
                    "get_student",
                    "cohort",
                    "role",
                    "educational_status",
                    "finantial_status",
                    "created_at",
                ],
                "list_filter": [
                    "role",
                    "educational_status",
                    "finantial_status",
                ],
                "search_fields": [
                    "user__email",
                    "user__first_name",
                    "user__last_name",
                    "cohort__name",
                    "cohort__slug",
                ],
            },
        },
    }

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("data", [{}, {"model_admin": "breathecode.admissions.admin.ValhallaAdmin"}])
def tests_admin_not_found(client: capy.Client, database: capy.Database, data: str):
    model = database.create(user={"is_staff": True})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {
        "detail": "model-admin-not-found",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def tests_action_not_found(client: capy.Client, database: capy.Database):
    model = database.create(user={"is_staff": True})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    data = {"model_admin": "breathecode.admissions.admin.CohortAdmin", "action": "not_a_valid_action"}
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {
        "detail": "action-not-found",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def tests_action_not_found(client: capy.Client, database: capy.Database):
    model = database.create(user={"is_staff": True})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    data = {"model_admin": "breathecode.admissions.admin.CohortAdmin", "action": "not_a_valid_action"}
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {
        "detail": "action-not-found",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def tests_bad_arguments(client: capy.Client, database: capy.Database):
    model = database.create(user={"is_staff": True})

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    data = {"model_admin": "breathecode.admissions.admin.CohortAdmin", "action": "mark_as_inactive", "arguments": []}
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {
        "detail": "arguments-must-be-a-dictionary",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("arguments, actions_ids", [({}, [1, 2, 3]), ({"id": 2}, [2]), ({"id__in": [2, 3]}, [2, 3])])
def tests_post(client: capy.Client, database: capy.Database, format: capy.Format, arguments: dict, actions_ids: list):
    def get_cohort_data(cohort):
        res = format.to_obj_repr(cohort)

        if cohort.id in actions_ids:
            res["stage"] = "INACTIVE"

        return res

    model = database.create(user={"is_staff": True}, cohort=(3, {"stage": "STARTED"}), city=1, country=1)

    client.force_authenticate(model.user)

    url = reverse_lazy("monitoring:admin_actions")
    data = {
        "model_admin": "breathecode.admissions.admin.CohortAdmin",
        "action": "mark_as_inactive",
        "arguments": arguments,
    }
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {
        "success": True,
    }

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert database.list_of("admissions.Cohort") == [get_cohort_data(x) for x in model.cohort]
