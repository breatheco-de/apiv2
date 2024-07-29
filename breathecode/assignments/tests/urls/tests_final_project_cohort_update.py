"""
Test /academy/cohort/<int:cohort_id>/final_project
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


def put_serializer(project, data={}):
    return {
        "id": project.id,
        "logo_url": project.logo_url,
        "name": project.name,
        "one_line_desc": project.one_line_desc,
        "public_url": project.public_url,
        "cohort": project.cohort.id if project.cohort else None,
        "created_at": project.created_at,
        "updated_at": project.created_at,
        "description": project.description,
        "screenshot": project.screenshot,
        "repo_url": project.repo_url,
        "slides_url": project.slides_url,
        "video_demo_url": project.video_demo_url,
        "visibility_status": project.visibility_status,
        "revision_status": project.revision_status,
        "project_status": project.project_status,
        "revision_message": project.revision_message,
        **data,
    }


def test_not_authenticated(bc: Breathecode, client: APIClient):

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})

    response = client.put(url, headers={"academy": 1})

    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
    json = response.json()

    assert json == expected
    assert response.status_code == 401


def test_no_capability(bc: Breathecode, client: APIClient):

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})
    model = bc.database.create(user=1)

    client.force_authenticate(model.user)

    response = client.put(url, headers={"academy": 1})

    expected = {"detail": "You (user: 1) don't have this capability: crud_assignment for academy 1", "status_code": 403}
    json = response.json()

    assert json == expected
    assert response.status_code == 403


def test_cohort_not_found(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1,
        role=1,
        capability="crud_assignment",
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 2, "final_project_id": 1})
    response = client.put(url, headers={"academy": 1})

    expected = {"detail": "cohort-not-found", "status_code": 404}
    json = response.json()

    assert expected == json
    assert response.status_code == 404


def test_project_not_found(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1,
        role=1,
        capability="crud_assignment",
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})
    response = client.put(url, headers={"academy": 1})

    expected = {"detail": "project-not-found", "status_code": 404}
    json = response.json()

    assert expected == json
    assert response.status_code == 404


def test_put_undone_project(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        cohort_user={"role": "STUDENT"},
        cohort=1,
        profile_academy=1,
        role=1,
        capability="crud_assignment",
        user=1,
        final_project={"members": [1]},
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})
    response = client.put(
        url,
        headers={"academy": 1},
        data={
            "revision_status": "APPROVED",
            "members": [1],
            "cohort": 1,
        },
    )

    expected = {"detail": "project-marked-approved-when-pending", "status_code": 400}
    json = response.json()

    assert expected == json
    assert response.status_code == 400


def test_no_github_members(bc: Breathecode, client: APIClient):

    model_cohort = bc.database.create(
        cohort=1,
        profile_academy=1,
        role=1,
        capability="crud_assignment",
    )

    cohort_user_model = bc.database.create(cohort_user={"cohort": model_cohort.cohort, "role": "STUDENT"})

    model = bc.database.create(
        user=1,
        final_project={"project_status": "DONE", "cohort": model_cohort.cohort, "members": [cohort_user_model.user]},
    )
    client.force_authenticate(model_cohort.user)

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})
    response = client.put(
        url,
        headers={"academy": 1},
        data={
            "project_status": "PENDING",
            "members": [2],
            "cohort": 1,
        },
    )

    expected = {"detail": "put-project-property-from-none-members", "status_code": 400}
    json = response.json()

    assert expected == json
    assert response.status_code == 400


def test_put_project(bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=2,
        cohort=1,
        profile_academy=1,
        role=1,
        capability="crud_assignment",
        cohort_user=[{"user_id": n + 1, "role": "STUDENT"} for n in range(2)],
        final_project={
            "members": [1],
            "project_status": "DONE",
        },
    )
    client.force_authenticate(model.user[0])

    url = reverse_lazy("assignments:final_project_cohort_update", kwargs={"cohort_id": 1, "final_project_id": 1})
    payload = {
        "project_status": "DONE",
        "revision_status": "APPROVED",
        "members": [2],
        "cohort": 1,
    }
    response = client.put(url, headers={"academy": 1}, data=payload)
    json = response.json()

    final_project = model.final_project
    expected = put_serializer(
        final_project,
        data={
            "created_at": bc.datetime.to_iso_string(final_project.created_at),
            "updated_at": json["updated_at"],
            **payload,
        },
    )

    assert expected == json
    assert response.status_code == 200
