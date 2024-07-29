import pytest
from unittest.mock import MagicMock, call

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.authenticate import tasks


@pytest.fixture(autouse=True)
def setup(db, enable_signals, monkeypatch):
    monkeypatch.setattr("breathecode.authenticate.tasks.create_user_from_invite.apply_async", MagicMock())
    enable_signals("breathecode.authenticate.signals.invite_status_updated")
    yield


@pytest.mark.parametrize("user_invite_with_user", [True, False])
@pytest.mark.parametrize("user_amount", [0, 2])
@pytest.mark.parametrize("status", ["PENDING", "WAITING_LIST", "REJECTED"])
def test_the_requirements_are_not_met(bc: Breathecode, fake, user_amount, status, user_invite_with_user):
    if user_invite_with_user and user_amount == 0:
        return

    email = fake.email()
    user_invite = {"status": status, "email": email, "user_id": None}
    if user_invite_with_user:
        user_invite["user_id"] = 1

    user = {"email": email}

    if user_amount:
        user = (user_amount, user)

    else:
        user = 0

    model = bc.database.create(user_invite=user_invite, user=user)

    assert bc.database.list_of("authenticate.UserInvite") == [bc.format.to_dict(model.user_invite)]

    if user_amount == 0:
        assert bc.database.list_of("auth.User") == []

    else:
        assert bc.database.list_of("auth.User") == bc.format.to_dict(model.user)

    assert tasks.create_user_from_invite.apply_async.call_args_list == []


def test_the_requirements_are_met(bc: Breathecode, fake):
    user_invites = [{"status": "ACCEPTED", "email": fake.email()} for _ in range(0, 2)]

    model = bc.database.create(user_invite=user_invites)

    assert bc.database.list_of("authenticate.UserInvite") == bc.format.to_dict(model.user_invite)
    assert bc.database.list_of("auth.User") == []
    assert tasks.create_user_from_invite.apply_async.call_args_list == [
        call(args=[1], countdown=60),
        call(args=[2], countdown=60),
    ]
