import logging
import os
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.authenticate.actions import get_verify_email_copy
from breathecode.authenticate.tasks import verify_user_invite_email
from breathecode.notify import actions
from breathecode.notify.actions import apply_verify_email_variant
from breathecode.notify.models import AcademyNotifySettings


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite.delay", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    yield


def _expected_email_data(invite, lang: str):
    data = get_verify_email_copy(invite, lang)
    data.update(
        {
            "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{invite.token}",
            "INVITE_ID": invite.id,
            "API_URL": os.getenv("API_URL", ""),
        }
    )
    return data


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


@pytest.mark.parametrize("lang", ["en", "es"])
def test_1_invite_with_user(database: capy.Database, format: capy.Format, lang: str):

    model = database.create(user_invite=1, user=1, user_setting={"lang": lang})

    verify_user_invite_email.delay(1)

    assert database.list_of("authenticate.UserInvite") == [format.to_obj_repr(model.user_invite)]
    assert database.list_of("auth.User") == [format.to_obj_repr(model.user)]

    assert actions.send_email_message.call_args_list == [
        call(
            "verify_email",
            model.user.email,
            _expected_email_data(model.user_invite, lang),
            academy=None,
        ),
    ]

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "generic"
    assert payload["SUBJECT"] == ("4Geeks - Validate account" if lang == "en" else "4Geeks - Valida tu cuenta")

    assert logging.Logger.error.call_args_list == []


@pytest.mark.parametrize("lang", ["en", "es"])
def test_1_invite_with_user_and_academy(database: capy.Database, format: capy.Format, lang: str):

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
            _expected_email_data(model.user_invite, lang),
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


def test_invite_with_event_context(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        city=1,
        country=1,
        academy=1,
        event={"slug": "python-workshop", "title": "Python Workshop"},
        user_invite={"event_slug": "python-workshop"},
    )
    invite = model.user_invite
    invite.user = model.user
    invite.save()

    actions.send_email_message.reset_mock()
    verify_user_invite_email.delay(invite.id)

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "event"
    assert payload["CONTEXT_NAME"] == "Python Workshop"
    assert payload["SUBJECT_EVENT"] == 'Finish setup to join the "{CONTEXT_NAME}" event'
    assert "{CONTEXT_NAME}" in payload["MESSAGE_EVENT"]


def test_invite_with_asset_context(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        asset={"slug": "intro-python", "title": "Intro to Python"},
        user_invite={"asset_slug": "intro-python"},
    )
    invite = model.user_invite
    invite.user = model.user
    invite.save()

    actions.send_email_message.reset_mock()
    verify_user_invite_email.delay(invite.id)

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "asset"
    assert payload["CONTEXT_NAME"] == "Intro to Python"
    assert payload["SUBJECT_ASSET"] == 'Finish setup to open "{CONTEXT_NAME}"'


def test_invite_with_course_context(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        city=1,
        country=1,
        academy=1,
        course=1,
        course_translation={"lang": "en", "title": "Full Stack Bootcamp", "description": "A course"},
        user_invite=1,
    )

    invite = model.user_invite
    invite.user = model.user
    invite.course = model.course
    invite.save()

    actions.send_email_message.reset_mock()
    verify_user_invite_email.delay(invite.id)

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "course"
    assert payload["CONTEXT_NAME"] == "Full Stack Bootcamp"


def test_invite_with_cohort_context(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        city=1,
        country=1,
        academy=1,
        cohort={"name": "Cohort 55"},
        user_invite=1,
    )

    invite = model.user_invite
    invite.user = model.user
    invite.cohort = model.cohort
    invite.save()

    actions.send_email_message.reset_mock()
    verify_user_invite_email.delay(invite.id)

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "cohort"
    assert payload["CONTEXT_NAME"] == "Cohort 55"


def test_event_priority_over_asset(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        city=1,
        country=1,
        academy=1,
        event={"slug": "live-event", "title": "Live Event"},
        asset={"slug": "some-asset", "title": "Some Asset"},
        user_invite={"event_slug": "live-event", "asset_slug": "some-asset"},
    )
    invite = model.user_invite
    invite.user = model.user
    invite.save()

    actions.send_email_message.reset_mock()
    verify_user_invite_email.delay(invite.id)

    payload = actions.send_email_message.call_args_list[0].args[2]
    assert payload["CONTEXT_TYPE"] == "event"
    assert payload["CONTEXT_NAME"] == "Live Event"


def test_apply_verify_email_variant_interpolates_context_name():
    data = {
        "CONTEXT_TYPE": "event",
        "CONTEXT_NAME": "Python Workshop",
        "SUBJECT_EVENT": 'Join "{CONTEXT_NAME}"',
        "MESSAGE_EVENT": 'Welcome to "{CONTEXT_NAME}"',
        "SUBJECT": "Generic subject",
        "MESSAGE": "Generic message",
    }

    apply_verify_email_variant(data)

    assert data["SUBJECT"] == 'Join "Python Workshop"'
    assert data["subject"] == 'Join "Python Workshop"'
    assert data["MESSAGE"] == 'Welcome to "Python Workshop"'


def test_academy_event_override_does_not_affect_asset(database: capy.Database):
    """SUBJECT_EVENT override must not change an asset-context email."""
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
        asset={"slug": "intro-python", "title": "Intro to Python"},
        user_invite={"asset_slug": "intro-python", "user_id": 1},
    )

    AcademyNotifySettings.objects.create(
        academy=model.academy,
        template_variables={
            "template.verify_email.SUBJECT_EVENT": "EVENT ONLY {CONTEXT_NAME}",
            "template.verify_email.MESSAGE_EVENT": "Event body {CONTEXT_NAME}",
        },
    )

    invite = model.user_invite
    data = get_verify_email_copy(invite, "en")
    data.update(model.academy.notify_settings.get_all_overrides_for_template("verify_email"))
    apply_verify_email_variant(data)

    assert data["CONTEXT_TYPE"] == "asset"
    assert data["SUBJECT"] == 'Finish setup to open "Intro to Python"'
    assert "EVENT ONLY" not in data["SUBJECT"]
    assert data["SUBJECT_EVENT"] == "EVENT ONLY {CONTEXT_NAME}"  # override present but unused


def test_academy_event_override_applies_for_event(database: capy.Database):
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
        event={"slug": "python-workshop", "title": "Python Workshop"},
        user_invite={"event_slug": "python-workshop", "user_id": 1},
    )

    AcademyNotifySettings.objects.create(
        academy=model.academy,
        template_variables={
            "template.verify_email.SUBJECT_EVENT": "Custom event: {CONTEXT_NAME}",
            "template.verify_email.MESSAGE_EVENT": "Custom body for {CONTEXT_NAME}",
        },
    )

    invite = model.user_invite
    data = get_verify_email_copy(invite, "en")
    data.update(model.academy.notify_settings.get_all_overrides_for_template("verify_email"))
    apply_verify_email_variant(data)

    assert data["CONTEXT_TYPE"] == "event"
    assert data["SUBJECT"] == "Custom event: Python Workshop"
    assert data["MESSAGE"] == "Custom body for Python Workshop"


def test_missing_event_falls_back_to_asset(database: capy.Database):
    model = database.create(
        user=1,
        user_setting={"lang": "en"},
        asset={"slug": "intro-python", "title": "Intro to Python"},
        user_invite={"event_slug": "does-not-exist", "asset_slug": "intro-python"},
    )

    copy = get_verify_email_copy(model.user_invite, "en")
    assert copy["CONTEXT_TYPE"] == "asset"
    assert copy["CONTEXT_NAME"] == "Intro to Python"
