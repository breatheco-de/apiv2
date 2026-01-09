"""
Tests for search filters on /v1/auth/academy/user/invite
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse_lazy

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import Capability, ProfileAcademy, Role, UserInvite

pytestmark = pytest.mark.django_db


@pytest.fixture
def academy_setup():
    capability = Capability.objects.create(slug="read_invite", description="Read invites")
    role = Role.objects.create(slug="staff", name="Staff")
    role.capabilities.add(capability)

    academy = Academy.objects.create(
        slug="test-academy",
        name="Test Academy",
        logo_url="https://example.com/logo.png",
        street_address="123 Main Street",
    )

    staff = User.objects.create(username="staff", email="staff@example.com")
    ProfileAcademy.objects.create(user=staff, academy=academy, role=role, email=staff.email, status="ACTIVE")

    return {"academy": academy, "staff": staff, "role": role}


def authenticate(client, staff, academy):
    client.force_authenticate(user=staff)
    client.credentials(HTTP_ACADEMY=str(academy.id))


def test_search_by_user_id(client, academy_setup):
    academy = academy_setup["academy"]
    staff = academy_setup["staff"]
    role = academy_setup["role"]

    user = User.objects.create(username="invitee", email="invitee@example.com")
    invite = UserInvite.objects.create(
        academy=academy,
        email=user.email,
        token="token-user-search",
        user=user,
        role=role,
        author=staff,
    )
    UserInvite.objects.create(
        academy=academy,
        email="other@example.com",
        token="token-user-search-other",
        role=role,
        author=staff,
    )

    authenticate(client, staff, academy)
    url = reverse_lazy("authenticate:academy_user_invite") + f"?user_id={user.id}"
    response = client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == invite.id


def test_search_by_invite_id(client, academy_setup):
    academy = academy_setup["academy"]
    staff = academy_setup["staff"]
    role = academy_setup["role"]

    target = UserInvite.objects.create(
        academy=academy,
        email="candidate@example.com",
        token="token-invite-search",
        role=role,
        author=staff,
    )
    UserInvite.objects.create(
        academy=academy,
        email="other@example.com",
        token="token-invite-search-other",
        role=role,
        author=staff,
    )

    authenticate(client, staff, academy)
    url = reverse_lazy("authenticate:academy_user_invite") + f"?invite_id={target.id}"
    response = client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == target.id


def test_search_by_profile_academy_id(client, academy_setup):
    academy = academy_setup["academy"]
    staff = academy_setup["staff"]
    role = academy_setup["role"]

    invitee = User.objects.create(username="profile-invitee", email="profile@example.com")
    profile = ProfileAcademy.objects.create(
        user=invitee,
        academy=academy,
        role=role,
        email="linked@example.com",
        status="INVITED",
    )
    target = UserInvite.objects.create(
        academy=academy,
        email=profile.email,
        token="token-profile-search",
        role=role,
        author=staff,
    )
    UserInvite.objects.create(
        academy=academy,
        email="other@example.com",
        token="token-profile-search-other",
        role=role,
        author=staff,
    )

    authenticate(client, staff, academy)
    url = reverse_lazy("authenticate:academy_user_invite") + f"?profile_academy_id={profile.id}"
    response = client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == target.id


def test_search_with_invalid_value(client, academy_setup):
    """Test that invalid non-numeric values are silently ignored"""
    academy = academy_setup["academy"]
    staff = academy_setup["staff"]
    role = academy_setup["role"]

    invite = UserInvite.objects.create(
        academy=academy,
        email="candidate@example.com",
        token="token-invalid-search",
        role=role,
        author=staff,
    )

    authenticate(client, staff, academy)
    # Invalid values are ignored, so we should get all pending invites
    url = reverse_lazy("authenticate:academy_user_invite") + "?user_id=abc,123"
    response = client.get(url)

    assert response.status_code == 200
    # Since "abc" is ignored and 123 doesn't exist, we should get all pending invites
    payload = response.json()
    assert len(payload) >= 1
    # The invite we created should be in the results
    invite_ids = [item["id"] for item in payload]
    assert invite.id in invite_ids


def test_search_with_multiple_values(client, academy_setup):
    """Test that multiple comma-separated values work correctly"""
    academy = academy_setup["academy"]
    staff = academy_setup["staff"]
    role = academy_setup["role"]

    user1 = User.objects.create(username="user1", email="user1@example.com")
    user2 = User.objects.create(username="user2", email="user2@example.com")
    user3 = User.objects.create(username="user3", email="user3@example.com")

    invite1 = UserInvite.objects.create(
        academy=academy,
        email=user1.email,
        token="token-multi-1",
        user=user1,
        role=role,
        author=staff,
    )
    invite2 = UserInvite.objects.create(
        academy=academy,
        email=user2.email,
        token="token-multi-2",
        user=user2,
        role=role,
        author=staff,
    )
    # This one should not be included
    UserInvite.objects.create(
        academy=academy,
        email="other@example.com",
        token="token-multi-other",
        role=role,
        author=staff,
    )

    authenticate(client, staff, academy)
    url = reverse_lazy("authenticate:academy_user_invite") + f"?user_id={user1.id},{user2.id}"
    response = client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    invite_ids = [item["id"] for item in payload]
    assert invite1.id in invite_ids
    assert invite2.id in invite_ids

