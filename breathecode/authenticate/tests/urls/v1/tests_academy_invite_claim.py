"""
Tests for PUT /v1/auth/academy/invite/<invite_id>/claim
and for the 4geeks-com union list behaviour in GET /v1/auth/academy/user/invite.
"""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse_lazy

from breathecode.admissions.models import Academy, City, Cohort, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role, UserInvite
from breathecode.marketing.models import Course

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _get_or_create_country():
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    return country


def _get_or_create_city(country=None):
    if country is None:
        country = _get_or_create_country()
    city, _ = City.objects.get_or_create(name="Test City", defaults={"country": country})
    return city


def _make_academy(slug, **kwargs):
    country = _get_or_create_country()
    city = _get_or_create_city(country)
    defaults = dict(
        name=slug,
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        city=city,
        country=country,
    )
    defaults.update(kwargs)
    return Academy.objects.create(slug=slug, **defaults)


def _make_role_with_capability(cap_slug, role_slug):
    cap, _ = Capability.objects.get_or_create(slug=cap_slug, defaults={"description": cap_slug})
    role, _ = Role.objects.get_or_create(slug=role_slug, defaults={"name": role_slug})
    role.capabilities.add(cap)
    return role


def _make_staff(academy, role, username=None):
    username = username or f"staff_{academy.slug}"
    user = User.objects.create(username=username, email=f"{username}@example.com")
    ProfileAcademy.objects.create(user=user, academy=academy, role=role, email=user.email, status="ACTIVE")
    return user


def _authenticate(client, user, academy):
    client.force_authenticate(user=user)
    client.credentials(HTTP_ACADEMY=str(academy.id))


def _make_invite(academy=None, status="PENDING", token_suffix="x", cohort=None, course=None, **kwargs):
    return UserInvite.objects.create(
        email=f"test-{token_suffix}@example.com",
        token=f"token-{token_suffix}",
        academy=academy,
        status=status,
        cohort=cohort,
        course=course,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# List union tests
# ---------------------------------------------------------------------------

class TestListUnionFor4GeeksCom:
    """GET /v1/auth/academy/user/invite includes null-academy invites only for 4geeks-com."""

    def setup_method(self):
        self.crud_role = _make_role_with_capability("crud_invite", "manager")
        self.read_role = _make_role_with_capability("read_invite", "reader")

    def test_4geeks_com_sees_own_and_null_invites(self, client):
        geeks = _make_academy("4geeks-com")
        other = _make_academy("other-academy")

        # Add read_invite capability to the role
        cap, _ = Capability.objects.get_or_create(slug="read_invite", defaults={"description": "read"})
        self.read_role.capabilities.add(cap)

        staff = _make_staff(geeks, self.read_role, username="geeks_staff")

        own_invite = _make_invite(academy=geeks, token_suffix="own")
        null_invite = _make_invite(academy=None, token_suffix="null")
        other_invite = _make_invite(academy=other, token_suffix="other")

        _authenticate(client, staff, geeks)
        url = reverse_lazy("authenticate:academy_user_invite")
        response = client.get(url)

        assert response.status_code == 200
        ids = {item["id"] for item in response.json()}
        assert own_invite.id in ids
        assert null_invite.id in ids
        assert other_invite.id not in ids

    def test_other_academy_only_sees_own_invites(self, client):
        geeks = _make_academy("4geeks-com")
        other = _make_academy("other-academy")

        cap, _ = Capability.objects.get_or_create(slug="read_invite", defaults={"description": "read"})
        self.read_role.capabilities.add(cap)

        staff = _make_staff(other, self.read_role, username="other_staff")

        own_invite = _make_invite(academy=other, token_suffix="other-own")
        null_invite = _make_invite(academy=None, token_suffix="other-null")

        _authenticate(client, staff, other)
        url = reverse_lazy("authenticate:academy_user_invite")
        response = client.get(url)

        assert response.status_code == 200
        ids = {item["id"] for item in response.json()}
        assert own_invite.id in ids
        assert null_invite.id not in ids

    def test_4geeks_com_academy_null_param_still_exclusive(self, client):
        """?academy=null still returns only null-academy invites."""
        geeks = _make_academy("4geeks-com")

        cap, _ = Capability.objects.get_or_create(slug="read_invite", defaults={"description": "read"})
        self.read_role.capabilities.add(cap)

        staff = _make_staff(geeks, self.read_role, username="geeks_staff2")

        own_invite = _make_invite(academy=geeks, token_suffix="gown")
        null_invite = _make_invite(academy=None, token_suffix="gnull")

        _authenticate(client, staff, geeks)
        url = reverse_lazy("authenticate:academy_user_invite") + "?academy=null"
        response = client.get(url)

        assert response.status_code == 200
        ids = {item["id"] for item in response.json()}
        assert null_invite.id in ids
        assert own_invite.id not in ids


# ---------------------------------------------------------------------------
# Claim endpoint tests
# ---------------------------------------------------------------------------

class TestClaimEndpoint:

    def setup_method(self):
        self.role = _make_role_with_capability("crud_invite", "claimer")

    def _url(self, invite_id):
        return reverse_lazy("authenticate:academy_invite_id_claim", kwargs={"invite_id": invite_id})

    def test_non_4geeks_com_academy_gets_403(self, client):
        other = _make_academy("another-academy")
        staff = _make_staff(other, self.role, username="other_claimer")
        invite = _make_invite(academy=None, token_suffix="c1")

        _authenticate(client, staff, other)
        response = client.put(self._url(invite.id))

        assert response.status_code == 403
        assert response.json()["detail"] == "claim-not-allowed"

    def test_missing_invite_returns_404(self, client):
        geeks = _make_academy("4geeks-com")
        staff = _make_staff(geeks, self.role, username="geeks_claimer")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(99999))

        assert response.status_code == 404
        assert response.json()["detail"] == "user-invite-not-found"

    def test_claim_unowned_null_academy_invite(self, client):
        geeks = _make_academy("4geeks-com")
        staff = _make_staff(geeks, self.role, username="geeks_claimer2")
        invite = _make_invite(academy=None, token_suffix="c3")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.academy_id == geeks.id

    def test_claim_already_owned_by_4geeks_com_is_idempotent(self, client):
        geeks = _make_academy("4geeks-com")
        staff = _make_staff(geeks, self.role, username="geeks_claimer3")
        invite = _make_invite(academy=geeks, token_suffix="c4")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 200
        assert response.json()["id"] == invite.id

    def test_claim_already_owned_by_other_academy_returns_409(self, client):
        geeks = _make_academy("4geeks-com")
        other = _make_academy("the-other-one")
        staff = _make_staff(geeks, self.role, username="geeks_claimer4")
        invite = _make_invite(academy=other, token_suffix="c5")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 409
        assert response.json()["detail"] == "invite-belongs-to-academy"
        assert "the-other-one" in response.json()["detail"] or response.json()["status_code"] == 409

    def test_claim_invite_with_cohort_of_other_academy_returns_409(self, client):
        geeks = _make_academy("4geeks-com")
        cohort_academy = _make_academy("cohort-owner")
        staff = _make_staff(geeks, self.role, username="geeks_claimer5")

        cohort = Cohort.objects.create(
            slug="test-cohort",
            name="Test Cohort",
            kickoff_date=timezone.now(),
            academy=cohort_academy,
        )
        invite = _make_invite(academy=None, token_suffix="c6", cohort=cohort)
        # Reset academy if save() filled it
        UserInvite.objects.filter(id=invite.id).update(academy=None)
        invite.refresh_from_db()

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "invite-belongs-to-academy"

    def test_claim_invite_with_cohort_of_4geeks_com_is_idempotent(self, client):
        geeks = _make_academy("4geeks-com")
        staff = _make_staff(geeks, self.role, username="geeks_claimer6")

        cohort = Cohort.objects.create(
            slug="geeks-cohort",
            name="Geeks Cohort",
            kickoff_date=timezone.now(),
            academy=geeks,
        )
        invite = _make_invite(academy=None, token_suffix="c7", cohort=cohort)
        # Ensure academy was NOT set by save() (in case backfill didn't run in test)
        UserInvite.objects.filter(id=invite.id).update(academy=None)
        invite.refresh_from_db()

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.academy_id == geeks.id

    def test_claim_non_pending_invite_returns_400(self, client):
        geeks = _make_academy("4geeks-com")
        staff = _make_staff(geeks, self.role, username="geeks_claimer7")
        invite = _make_invite(academy=None, status="ACCEPTED", token_suffix="c8")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 400
        assert response.json()["detail"] == "invite-not-pending"

    def test_claim_requires_authentication(self, client):
        geeks = _make_academy("4geeks-com")
        invite = _make_invite(academy=None, token_suffix="c9")

        client.credentials(HTTP_ACADEMY=str(geeks.id))
        response = client.put(self._url(invite.id))

        assert response.status_code == 401

    def test_claim_requires_crud_invite_capability(self, client):
        geeks = _make_academy("4geeks-com")
        # Create a role without crud_invite
        no_cap_role, _ = Role.objects.get_or_create(slug="nocap", defaults={"name": "No Cap"})
        staff = _make_staff(geeks, no_cap_role, username="geeks_nocap")

        invite = _make_invite(academy=None, token_suffix="c10")

        _authenticate(client, staff, geeks)
        response = client.put(self._url(invite.id))

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Model save: implied academy tests
# ---------------------------------------------------------------------------

class TestUserInviteSaveImpliesAcademy:

    def test_save_sets_academy_from_cohort(self):
        academy = _make_academy("cohort-acad")
        cohort = Cohort.objects.create(
            slug="save-cohort",
            name="Save Cohort",
            kickoff_date=timezone.now(),
            academy=academy,
        )
        invite = UserInvite(
            email="save-cohort@example.com",
            token="token-save-cohort",
            cohort=cohort,
        )
        invite.save()

        invite.refresh_from_db()
        assert invite.academy_id == academy.id
