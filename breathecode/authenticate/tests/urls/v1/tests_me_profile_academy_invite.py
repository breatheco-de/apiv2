import pytest
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin import Breathecode


# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


def put_serializer(profile_academy, data={}):

    return {
        "id": profile_academy.id,
        "first_name": profile_academy.first_name,
        "last_name": profile_academy.last_name,
        "user": {
            "id": profile_academy.user.id,
            "email": profile_academy.user.email,
            "first_name": profile_academy.user.first_name,
            "last_name": profile_academy.user.last_name,
            "profile": None,
        },
        "academy": {
            "id": profile_academy.academy.id,
            "name": profile_academy.academy.name,
            "slug": profile_academy.academy.slug,
        },
        "role": {"id": profile_academy.role.slug, "slug": profile_academy.role.slug, "name": profile_academy.role.name},
        "created_at": profile_academy.created_at,
        "email": profile_academy.email,
        "address": profile_academy.address,
        "phone": profile_academy.phone,
        "status": profile_academy.status,
        **data,
    }


def test_with_no_auth(bc: Breathecode, client):

    url = reverse_lazy("auth:me_profile_academy_invite", kwargs={"profile_academy_id": 1, "new_status": "active"})
    response = client.put(url)
    json = response.json()

    expected = {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_active_profile_academy_not_found(bc: Breathecode, client):

    model = bc.database.create(user=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("auth:me_profile_academy_invite", kwargs={"profile_academy_id": 1, "new_status": "active"})

    response = client.put(url)
    json = response.json()

    expected = {"detail": "profile-academy-not-found", "status_code": status.HTTP_400_BAD_REQUEST}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_someone_else_profile_academy(bc: Breathecode, client):

    model = bc.database.create(user=2, profile_academy=1)
    client.force_authenticate(model.user[1])

    url = reverse_lazy("auth:me_profile_academy_invite", kwargs={"profile_academy_id": 1, "new_status": "active"})

    response = client.put(url)
    json = response.json()

    expected = {"detail": "profile-academy-not-found", "status_code": status.HTTP_400_BAD_REQUEST}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_active_profile_wrong_status(bc: Breathecode, client):

    model = bc.database.create(user=1, profile_academy=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("auth:me_profile_academy_invite", kwargs={"profile_academy_id": 1, "new_status": "sss"})

    response = client.put(url)
    json = response.json()

    expected = {"detail": "invalid-status", "status_code": status.HTTP_400_BAD_REQUEST}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_active_profile_academy(bc: Breathecode, client):

    model = bc.database.create(user=1, profile_academy=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("auth:me_profile_academy_invite", kwargs={"profile_academy_id": 1, "new_status": "active"})

    response = client.put(url)
    json = response.json()

    expected = put_serializer(
        model.profile_academy,
        data={"status": "ACTIVE", "created_at": bc.datetime.to_iso_string(model.profile_academy.created_at)},
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
