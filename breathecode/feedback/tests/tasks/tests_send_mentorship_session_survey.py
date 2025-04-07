"""
Tasks tests
"""

from datetime import timedelta
from typing import Callable
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from django.utils import timezone

import breathecode.notify.actions as actions
from breathecode.authenticate.models import Token

from ...tasks import send_mentorship_session_survey
from ...utils import strings


def get_translations(lang, template):
    return {
        "title": strings[lang][template]["title"],
        "highest": strings[lang][template]["highest"],
        "lowest": strings[lang][template]["lowest"],
        "survey_subject": strings[lang][template]["survey_subject"],
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock())
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("os.getenv", MagicMock(side_effect=apply_get_env({"ENV": "test", "API_URL": API_URL})))
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    monkeypatch.setattr("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())


API_URL = "http://kenny-was.reborn"
UTC_NOW = timezone.now()
# SurveyTemplate


def build_answer_dict(attrs={}):
    return {
        "asset_id": None,
        "live_class_id": None,
        "academy_id": None,
        "cohort_id": None,
        "comment": None,
        "event_id": None,
        "highest": "very likely",
        "id": 1,
        "lang": "en",
        "lowest": "not likely",
        "mentor_id": None,
        "mentorship_session_id": None,
        "opened_at": None,
        "score": None,
        "sent_at": None,
        "status": "PENDING",
        "survey_id": None,
        "title": None,
        "token_id": None,
        "user_id": None,
        **attrs,
    }


def apply_get_env(envs={}):

    def get_env(key, default=None):
        return envs.get(key, default)

    return get_env


# """
# 🔽🔽🔽 Without MentorshipSession
# """


def test_send_mentorship_session_survey__without_mentorship_session(database: capy.Database):
    from logging import Logger

    send_mentorship_session_survey.delay(1)

    assert database.list_of("feedback.Answer") == []
    assert Logger.info.call_args_list == [
        call("Starting send_mentorship_session_survey"),
        call("Starting send_mentorship_session_survey"),
    ]
    assert Logger.error.call_args_list == [
        call("Mentoring session doesn't found", exc_info=True),
    ]
    assert actions.send_email_message.call_args_list == []


# """
# 🔽🔽🔽 With MentorshipSession and without User (mentee)
# """


def test_send_mentorship_session_survey__with_mentorship_session(database: capy.Database):
    from logging import Logger

    model = database.create(city=1, country=1, mentorship_session={"mentee_id": None})
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert database.list_of("feedback.Answer") == []
    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == [
        call("This session doesn't have a mentee", exc_info=True),
    ]
    assert actions.send_email_message.call_args_list == []


# """
# 🔽🔽🔽 With MentorshipSession started not finished and with User (mentee)
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_started_not_finished(
    database: capy.Database,
):
    from logging import Logger

    mentorship_session = {
        "started_at": UTC_NOW,
    }
    database.create(city=1, country=1, mentorship_session=mentorship_session, user=1)
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == [
        call("This session hasn't finished", exc_info=True),
    ]

    assert database.list_of("feedback.Answer") == []
    assert actions.send_email_message.call_args_list == []
    assert database.list_of("authenticate.Token") == []


# """
# 🔽🔽🔽 With MentorshipSession not started but finished and with User (mentee)
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_not_started_but_finished(
    database: capy.Database,
):
    from logging import Logger

    mentorship_session = {
        "ended_at": UTC_NOW,
    }
    database.create(city=1, country=1, mentorship_session=mentorship_session, user=1)
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == [
        call("This session hasn't finished", exc_info=True),
    ]

    assert database.list_of("feedback.Answer") == []
    assert actions.send_email_message.call_args_list == []
    assert database.list_of("authenticate.Token") == []


# """
# 🔽🔽🔽 With MentorshipSession started and finished and with User (mentee)
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_started_and_finished(
    database: capy.Database,
):
    from logging import Logger

    mentorship_session = {
        "started_at": UTC_NOW,
        "ended_at": UTC_NOW + timedelta(minutes=5),
    }
    database.create(city=1, country=1, mentorship_session=mentorship_session, user=1)
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == [
        call("Mentorship session duration is less or equal than five minutes", exc_info=True),
    ]

    assert database.list_of("feedback.Answer") == []
    assert actions.send_email_message.call_args_list == []
    assert database.list_of("authenticate.Token") == []


# """
# 🔽🔽🔽 With MentorshipSession and with User (mentee)
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee(database: capy.Database):
    from logging import Logger

    mentorship_session = {
        "started_at": UTC_NOW,
        "ended_at": UTC_NOW + timedelta(minutes=5, seconds=1),
    }
    model = database.create(city=1, country=1, mentorship_session=mentorship_session, user=1)
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == [
        call("Mentorship session doesn't have a service associated with it", exc_info=True),
    ]

    assert database.list_of("feedback.Answer") == []
    assert actions.send_email_message.call_args_list == []
    assert database.list_of("authenticate.Token") == []


# """
# 🔽🔽🔽 With MentorshipSession, User (mentee) and MentorshipService
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {
                "lang": "en",
                "is_shared": True,
                "when_asking_mentorshipsession": get_translations("en", "mentorship_session"),
            },
            {
                "lang": "es",
                "is_shared": True,
                "when_asking_mentorshipsession": get_translations("es", "mentorship_session"),
                "original_id": 1,
            },
        ],
    ],
)
def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_mentorship_service(
    database: capy.Database,
    survey_template: list[dict],
    partial_equality: Callable,
):
    from logging import Logger

    mentorship_session = {
        "started_at": UTC_NOW,
        "ended_at": UTC_NOW + timedelta(minutes=5, seconds=1),
    }
    model = database.create(
        city=1,
        country=1,
        mentorship_session=mentorship_session,
        user=1,
        mentorship_service=1,
        survey_template=survey_template,
    )
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]
    assert Logger.error.call_args_list == []

    fullname_of_mentor = (
        model.mentorship_session.mentor.user.first_name + " " + model.mentorship_session.mentor.user.last_name
    )

    token = Token.objects.get(id=1)

    assert database.list_of("feedback.Answer") == [
        build_answer_dict(
            {
                "academy_id": 1,
                "title": strings["en"]["mentorship_session"]["title"].format(fullname_of_mentor),
                "lowest": strings["en"]["mentorship_session"]["lowest"],
                "highest": strings["en"]["mentorship_session"]["highest"],
                "mentorship_session_id": 1,
                "sent_at": UTC_NOW,
                "status": "SENT",
                "question_by_slug": None,
                "user_id": 1,
                "token_id": 1,
            }
        ),
    ]

    assert actions.send_email_message.call_args_list == [
        call(
            "nps_survey",
            model.user.email,
            {
                "SUBJECT": strings["en"]["survey_subject"],
                "MESSAGE": strings["en"]["mentorship_session"]["title"].format(fullname_of_mentor),
                "TRACKER_URL": f"{API_URL}/v1/feedback/answer/1/tracker.png",
                "BUTTON": strings["en"]["button_label"],
                "LINK": f"https://nps.4geeks.com/1?token={token.key}",
            },
            academy=model.academy,
        )
    ]

    partial_equality(
        database.list_of("authenticate.Token"),
        [
            {
                "key": token.key,
                "token_type": "temporal",
            }
        ],
    )


# """
# 🔽🔽🔽 With MentorshipSession, with User (mentee) and Answer with status PENDING
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_answer(
    database: capy.Database,
    format: capy.Format,
    partial_equality: Callable,
):
    from logging import Logger

    mentorship_session = {
        "started_at": UTC_NOW,
        "ended_at": UTC_NOW + timedelta(minutes=5, seconds=1),
    }
    model = database.create(
        city=1, country=1, mentorship_session=mentorship_session, user=1, feedback__answer=1, mentorship_service=1
    )
    model.token.delete()
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [
        call("Starting send_mentorship_session_survey"),
    ]
    assert Logger.error.call_args_list == []

    assert database.list_of("feedback.Answer") == [
        {
            **format.to_obj_repr(model.feedback__answer),
            "sent_at": UTC_NOW,
            "token_id": 2,
        },
    ]
    token = Token.objects.get(id=2)

    assert actions.send_email_message.call_args_list == [
        call(
            "nps_survey",
            model.user.email,
            {
                "SUBJECT": strings["en"]["survey_subject"],
                "MESSAGE": model.feedback__answer.title,
                "TRACKER_URL": f"{API_URL}/v1/feedback/answer/1/tracker.png",
                "BUTTON": strings["en"]["button_label"],
                "LINK": f"https://nps.4geeks.com/1?token={token.key}",
            },
            academy=model.academy,
        )
    ]

    partial_equality(
        database.list_of("authenticate.Token"),
        [
            {
                "key": token.key,
                "token_type": "temporal",
            }
        ],
    )


# """
# 🔽🔽🔽 With MentorshipSession, with User (mentee) and Answer with status ANSWERED
# """


def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_answer_answered(
    database: capy.Database,
    format: capy.Format,
):
    from logging import Logger

    answer = {"status": "ANSWERED"}
    mentorship_session = {
        "started_at": UTC_NOW,
        "ended_at": UTC_NOW + timedelta(minutes=5, seconds=1),
    }
    model = database.create(
        city=1, country=1, mentorship_session=mentorship_session, user=1, feedback__answer=answer, mentorship_service=1
    )
    model.token.delete()
    Logger.info.call_args_list = []

    send_mentorship_session_survey.delay(1)

    assert Logger.info.call_args_list == [call("Starting send_mentorship_session_survey")]

    assert Logger.error.call_args_list == [
        call("This survey about MentorshipSession 1 was answered", exc_info=True),
    ]
    assert database.list_of("feedback.Answer") == [
        {
            **format.to_obj_repr(model.feedback__answer),
            "token_id": None,
        },
    ]
    assert actions.send_email_message.call_args_list == []
    assert database.list_of("authenticate.Token") == []
