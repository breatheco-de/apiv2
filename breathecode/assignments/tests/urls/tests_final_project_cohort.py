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


def get_serializer(final_project, data={}):
    return {
        "id": final_project.id,
        "repo_owner": (
            {
                "id": final_project.repo_owner.id,
                "first_name": final_project.repo_owner.first_name,
                "last_name": final_project.repo_owner.last_name,
            }
            if final_project.repo_owner
            else None
        ),
        "name": final_project.name,
        "one_line_desc": final_project.one_line_desc,
        "description": final_project.description,
        "project_status": final_project.project_status,
        "revision_status": final_project.revision_status,
        "visibility_status": final_project.visibility_status,
        "repo_url": final_project.repo_url,
        "public_url": final_project.public_url,
        "logo_url": final_project.logo_url,
        "screenshot": final_project.screenshot,
        "slides_url": final_project.slides_url,
        "video_demo_url": final_project.video_demo_url,
        "cohort": (
            {"id": final_project.cohort.id, "name": final_project.cohort.name, "slug": final_project.cohort.slug}
            if final_project.cohort
            else None
        ),
        "created_at": final_project.created_at,
        "updated_at": final_project.updated_at,
        "members": [members_serializer(member) for member in final_project.members.all()],
        **data,
    }


def members_serializer(member, data={}):
    return {
        "id": member.id,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "profile": {"avatar_url": member.profile.avatar_url} if member.profile is not None else None,
    }


def test_not_authenticated(bc: Breathecode, client: APIClient):

    url = reverse_lazy("assignments:final_project_cohort", kwargs={"cohort_id": 1})

    response = client.get(url, headers={"academy": 1})

    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
    json = response.json()

    assert json == expected
    assert response.status_code == 401


def test_no_capability(bc: Breathecode, client: APIClient):

    url = reverse_lazy("assignments:final_project_cohort", kwargs={"cohort_id": 1})
    model = bc.database.create(user=1)

    client.force_authenticate(model.user)

    response = client.get(url, headers={"academy": 1})

    expected = {"detail": "You (user: 1) don't have this capability: read_assignment for academy 1", "status_code": 403}
    json = response.json()

    assert json == expected
    assert response.status_code == 403


def test_cohort_not_found(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1,
        role=1,
        capability="read_assignment",
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:final_project_cohort", kwargs={"cohort_id": 2})
    response = client.get(url, headers={"academy": 1})

    expected = {"detail": "cohort-not-found", "status_code": 404}
    json = response.json()

    assert expected == json
    assert response.status_code == 404


def test_with_no_projects(bc: Breathecode, client: APIClient):

    model = bc.database.create(
        profile_academy=1,
        role=1,
        cohort=1,
        capability="read_assignment",
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:final_project_cohort", kwargs={"cohort_id": 1})
    response = client.get(url, headers={"academy": 1})

    expected = []
    json = response.json()

    assert expected == json
    assert response.status_code == 200


def test_with_projects(bc: Breathecode, client: APIClient):

    model_cohort = bc.database.create(
        cohort=1,
        profile_academy=1,
        role=1,
        capability="read_assignment",
    )

    model = bc.database.create(
        final_project={"cohort": model_cohort.cohort},
    )

    client.force_authenticate(model_cohort.user)

    url = reverse_lazy("assignments:final_project_cohort", kwargs={"cohort_id": 1})
    response = client.get(url, headers={"academy": 1})

    project = model.final_project
    expected = [
        get_serializer(
            project,
            {
                "created_at": bc.datetime.to_iso_string(project.created_at),
                "updated_at": bc.datetime.to_iso_string(project.updated_at),
            },
        )
    ]
    json = response.json()

    assert expected == json
    assert response.status_code == 200
