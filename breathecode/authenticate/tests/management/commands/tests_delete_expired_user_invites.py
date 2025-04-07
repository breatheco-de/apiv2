import pytest
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from breathecode.authenticate.management.commands.delete_expired_user_invites import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

NOW = timezone.now()
FIXED_PASSWORD = make_password("pass1234")
FIXED_TOKEN = "fixed-token-for-testing-123"

# Base user data that will be used in all tests
BASE_USER_DATA = {
    "password": FIXED_PASSWORD,
    "date_joined": NOW,
}

# Base invite data that will be used in all tests
BASE_INVITE_DATA = {
    "token": FIXED_TOKEN,
    "author_id": None,
}


def user_serializer(user, data={}):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "last_login": None,
        "date_joined": NOW,
        "password": FIXED_PASSWORD,
        **data,
    }


def user_invite_serializer(invite, data={}):
    return {
        "id": invite.id,
        "user_id": invite.user.id if invite.user else None,
        "status": invite.status,
        "expires_at": invite.expires_at,
        "academy_id": None,
        "asset_slug": None,
        "author_id": None,
        "city": None,
        "cohort_id": None,
        "country": None,
        "email": None,
        "event_slug": None,
        "first_name": None,
        "has_marketing_consent": False,
        "is_email_validated": False,
        "last_name": None,
        "latitude": None,
        "longitude": None,
        "phone": "",
        "process_message": "",
        "process_status": "PENDING",
        "role_id": None,
        "sent_at": None,
        "syllabus_id": None,
        "token": invite.token,
        "conversion_info": None,
        "email_quality": None,
        "email_status": None,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("django.utils.timezone.now", lambda: NOW)
    yield


# When: running the command and there are no expired pending user invites
# Then: it should not delete anything
def test_no_expired_invites(bc: Breathecode):
    future = NOW + timezone.timedelta(days=1)

    # Create non-expired pending invite
    model = bc.database.create(
        user=BASE_USER_DATA,
        user_invite={
            "status": "PENDING",
            "expires_at": future,
            **BASE_INVITE_DATA,
        },
    )

    command = Command()
    command.handle()

    # Verify nothing was deleted
    assert bc.database.list_of("auth.User") == [user_serializer(model.user)]
    assert bc.database.list_of("authenticate.UserInvite") == [user_invite_serializer(model.user_invite)]


# When: there are expired pending user invites with no other conditions
# Then: it should delete both the invite and the user
def test_expired_invite_delete(bc: Breathecode):
    past = NOW - timezone.timedelta(days=1)

    # Create expired pending invite
    model = bc.database.create(
        user=BASE_USER_DATA,
        user_invite={
            "user_id": 1,
            "status": "PENDING",
            "expires_at": past,
            **BASE_INVITE_DATA,
        },
    )

    command = Command()
    command.handle()

    # Verify both user and invite were deleted
    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("authenticate.UserInvite") == []


# When: user has another non-expired pending invite
# Then: it should only delete the expired invite but keep the user
def test_user_has_other_pending_invite(bc: Breathecode):
    past = NOW - timezone.timedelta(days=1)
    future = NOW + timezone.timedelta(days=1)

    token = "yyyyy"

    # Create one expired and one non-expired invite for same user
    model = bc.database.create(user=BASE_USER_DATA)
    bc.database.create(
        user_invite={
            "user_id": 1,
            "status": "PENDING",
            "expires_at": past,
            **BASE_INVITE_DATA,
        }
    )
    future_invite = bc.database.create(
        user_invite={
            "user_id": 1,
            "status": "PENDING",
            "expires_at": future,
            **BASE_INVITE_DATA,
            "token": token,
        }
    ).user_invite

    command = Command()
    command.handle()

    # Verify only expired invite was deleted
    assert bc.database.list_of("auth.User") == [user_serializer(model.user)]
    assert bc.database.list_of("authenticate.UserInvite") == [user_invite_serializer(future_invite)]


# When: user has an accepted invite
# Then: it should only delete the expired invite but keep the user
def test_user_has_accepted_invite(bc: Breathecode):
    past = NOW - timezone.timedelta(days=1)

    token = "yyyyy"

    # Create one expired pending and one accepted invite for same user
    model = bc.database.create(user=BASE_USER_DATA)
    bc.database.create(
        user_invite={
            "user_id": 1,
            "status": "PENDING",
            "expires_at": past,
            **BASE_INVITE_DATA,
        }
    )
    accepted_invite = bc.database.create(
        user_invite={
            "user_id": 1,
            "status": "ACCEPTED",
            "expires_at": past,
            **BASE_INVITE_DATA,
            "token": token,
        }
    ).user_invite

    command = Command()
    command.handle()

    # Verify only expired pending invite was deleted
    assert bc.database.list_of("auth.User") == [user_serializer(model.user)]
    assert bc.database.list_of("authenticate.UserInvite") == [user_invite_serializer(accepted_invite)]


# When: user has a profile academy
# Then: it should only delete the expired invite but keep the user
def test_user_has_profile_academy(bc: Breathecode):
    past = NOW - timezone.timedelta(days=1)

    # Create user with expired invite and profile academy
    model = bc.database.create(
        user=BASE_USER_DATA,
        profile_academy=1,
        user_invite={
            "user_id": 1,
            "status": "PENDING",
            "expires_at": past,
            **BASE_INVITE_DATA,
        },
    )

    command = Command()
    command.handle()

    # Verify only expired invite was deleted
    assert bc.database.list_of("auth.User") == [user_serializer(model.user)]
    assert bc.database.list_of("authenticate.UserInvite") == []
    assert len(bc.database.list_of("authenticate.ProfileAcademy")) == 1


# When: invite has no associated user
# Then: it should just delete the invite
def test_invite_without_user(bc: Breathecode):
    past = NOW - timezone.timedelta(days=1)

    # Create expired invite with no user
    bc.database.create(
        user_invite={
            "user_id": None,
            "status": "PENDING",
            "expires_at": past,
            **BASE_INVITE_DATA,
        }
    )

    command = Command()
    command.handle()

    # Verify invite was deleted
    assert bc.database.list_of("authenticate.UserInvite") == []
