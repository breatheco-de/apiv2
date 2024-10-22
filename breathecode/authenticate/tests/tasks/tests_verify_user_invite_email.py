import logging
import random
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.authenticate.tasks import verify_user_invite_email
from breathecode.notify import actions


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite.delay", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    yield


def test_no_invite(database: capy.Database):

    verify_user_invite_email.delay(1)

    assert database.list_of("authenticate.UserInvite") == []
    assert database.list_of("auth.User") == []

    assert actions.send_email_message.call_args_list == []

    assert logging.Logger.error.call_args_list == [
        call("User invite 1 not found", exc_info=True),
    ]


def test_1_invite(database: capy.Database, format: capy.Format):

    model = database.create(user_invite=1)

    verify_user_invite_email.delay(1)

    assert database.list_of("authenticate.UserInvite") == [format.to_obj_repr(model.user_invite)]
    assert database.list_of("auth.User") == []

    assert actions.send_email_message.call_args_list == []

    assert logging.Logger.error.call_args_list == [
        call("User not found for user invite 1", exc_info=True),
    ]


@pytest.mark.parametrize(
    "lang, subject",
    [
        ("en", "4Geeks - Validate account"),
        ("es", "4Geeks - Valida tu cuenta"),
    ],
)
def test_1_invite_with_user(database: capy.Database, format: capy.Format, lang: str, subject: str):

    model = database.create(user_invite=1, user=1, user_setting={"lang": lang})

    verify_user_invite_email.delay(1)

    assert database.list_of("authenticate.UserInvite") == [format.to_obj_repr(model.user_invite)]
    assert database.list_of("auth.User") == [format.to_obj_repr(model.user)]

    assert actions.send_email_message.call_args_list == [
        call(
            "verify_email",
            model.user.email,
            {
                "SUBJECT": subject,
                "LANG": lang,
                "LINK": f"/v1/auth/password/{model.user_invite.token}",
            },
            academy=None,
        ),
    ]

    assert logging.Logger.error.call_args_list == []


@pytest.mark.parametrize(
    "lang, subject",
    [
        ("en", "4Geeks - Validate account"),
        ("es", "4Geeks - Valida tu cuenta"),
    ],
)
def test_1_invite_with_user_and_academy(database: capy.Database, format: capy.Format, lang: str, subject: str):

    model = database.create(
        user_invite=1,
        user=1,
        user_setting={"lang": lang},
        academy=1,
        city=1,
        country=1,
    )

    verify_user_invite_email.delay(1)

    assert database.list_of("authenticate.UserInvite") == [format.to_obj_repr(model.user_invite)]
    assert database.list_of("auth.User") == [format.to_obj_repr(model.user)]

    assert actions.send_email_message.call_args_list == [
        call(
            "verify_email",
            model.user.email,
            {
                "SUBJECT": subject,
                "LANG": lang,
                "LINK": f"/v1/auth/password/{model.user_invite.token}",
            },
            academy=model.academy,
        ),
    ]

    assert logging.Logger.error.call_args_list == []


@pytest.mark.parametrize("validated_in_the_past", [True, False])
def test_1_invite_validated(database: capy.Database, format: capy.Format, validated_in_the_past: bool):

    if validated_in_the_past:
        user_invite = [
            {"is_email_validated": True},
            {"is_email_validated": False},
        ]
    else:
        user_invite = {"is_email_validated": True}

    model = database.create(
        user_invite=user_invite,
        user=1,
        academy=1,
        city=1,
        country=1,
    )

    id = 2 if validated_in_the_past else 1
    verify_user_invite_email.delay(id)

    if validated_in_the_past:
        db = [
            format.to_obj_repr(model.user_invite[0]),
            format.to_obj_repr(model.user_invite[1]),
        ]
    else:
        db = [format.to_obj_repr(model.user_invite)]

    assert database.list_of("authenticate.UserInvite") == db
    assert database.list_of("auth.User") == [format.to_obj_repr(model.user)]

    assert actions.send_email_message.call_args_list == []

    assert logging.Logger.error.call_args_list == [call("Email already validated for user 1", exc_info=True)]
