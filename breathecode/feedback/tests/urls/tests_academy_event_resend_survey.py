"""
Test POST /academy/event/<event_id>/resend_survey
"""

from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.authenticate.models import Token
from breathecode.events.models import FINISHED
from breathecode.feedback.models import AcademyFeedbackSettings, Answer, SurveyTemplate
from breathecode.feedback.utils import strings

pytestmark = pytest.mark.django_db

API_URL = "http://kenny-was.reborn"
UTC_NOW = timezone.now()


def apply_get_env(envs=None):
    envs = envs or {}

    def get_env(key, default=None):
        return envs.get(key, default)

    return get_env


def event_translations(lang):
    return {
        "title": strings[lang]["event"]["title"],
        "highest": strings[lang]["event"]["highest"],
        "lowest": strings[lang]["event"]["lowest"],
        "survey_subject": strings[lang]["event"]["survey_subject"],
    }


def setup_event_survey(academy):
    template = SurveyTemplate.objects.create(
        slug=f"event-nps-{academy.id}",
        lang="en",
        academy=academy,
        is_shared=True,
        when_asking_event=event_translations("en"),
    )
    AcademyFeedbackSettings.objects.create(academy=academy, event_survey_template=template)
    return template


def create_finished_event(database, **event_kwargs):
    defaults = {
        "status": FINISHED,
        "ended_at": UTC_NOW,
        "ending_at": UTC_NOW - timedelta(hours=1),
        "lang": "en",
    }
    defaults.update(event_kwargs)
    return database.create(city=1, country=1, academy=1, event=defaults)


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock(return_value=True))
    monkeypatch.setattr("os.getenv", MagicMock(side_effect=apply_get_env({"ENV": "test", "API_URL": API_URL})))


def test_resend_survey__without_auth(client):
    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": 1})
    response = client.post(url, data={}, content_type="application/json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
def test_resend_survey__without_capability(client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    database.create(authenticate=True, profile_academy=1, role=1, capability="read_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
def test_resend_survey__event_not_found(client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": 9999})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["slug"] == "event-not-found"


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
def test_resend_survey__event_not_finished(client, database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        event={
            "status": "ACTIVE",
            "ending_at": UTC_NOW + timedelta(hours=2),
            "ended_at": None,
            "lang": "en",
        },
        authenticate=True,
        profile_academy=1,
        role=1,
        capability="crud_survey",
    )
    setup_event_survey(model.academy)

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["slug"] == "event-not-finished"


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
def test_resend_survey__no_template_configured(client, database):
    model = create_finished_event(database)
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["slug"] == "event-survey-template-not-configured"


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.feedback.tasks.send_event_answer_email.delay", MagicMock())
def test_resend_survey__creates_and_schedules_for_attendee(send_email_task_mock, client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    attendee = database.create(user=1).user
    database.create(
        event_checkin={
            "event": model.event,
            "attendee": attendee,
            "attended_at": UTC_NOW,
            "status": "DONE",
            "email": attendee.email,
        }
    )
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["event_id"] == model.event.id
    assert len(json["created"]) == 1
    assert json["created"][0]["user_id"] == attendee.id
    assert json["created"][0]["scheduled"] is True
    assert json["resent"] == []
    assert json["skipped_answered"] == []

    answer = Answer.objects.get(event=model.event, user=attendee)
    send_email_task_mock.assert_called_once_with(answer.id)


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.feedback.tasks.send_event_answer_email.delay", MagicMock())
def test_resend_survey__skips_answered(send_email_task_mock, client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    attendee = database.create(user=1).user
    database.create(
        event_checkin={
            "event": model.event,
            "attendee": attendee,
            "attended_at": UTC_NOW,
            "status": "DONE",
            "email": attendee.email,
        },
        feedback__answer={
            "event": model.event,
            "user": attendee,
            "academy": model.academy,
            "status": "ANSWERED",
            "score": 9,
        },
    )
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["skipped_answered"]) == 1
    assert json["skipped_answered"][0]["user_id"] == attendee.id
    assert json["created"] == []
    assert json["resent"] == []
    send_email_task_mock.assert_not_called()


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.feedback.tasks.send_event_answer_email.delay", MagicMock())
def test_resend_survey__resends_non_answered(send_email_task_mock, client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    attendee = database.create(user=1).user
    database.create(
        event_checkin={
            "event": model.event,
            "attendee": attendee,
            "attended_at": UTC_NOW,
            "status": "DONE",
            "email": attendee.email,
        },
        feedback__answer={
            "event": model.event,
            "user": attendee,
            "academy": model.academy,
            "status": "SENT",
            "title": "Old title",
        },
        token=1,
    )
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["resent"]) == 1
    assert json["resent"][0]["user_id"] == attendee.id
    assert json["created"] == []

    answer = Answer.objects.get(event=model.event, user=attendee)
    send_email_task_mock.assert_called_once_with(answer.id)
    assert answer.title == strings["en"]["event"]["title"]


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
def test_resend_survey__dry_run(client, database):
    model = create_finished_event(database)
    setup_event_survey(model.academy)
    attendee = database.create(user=1).user
    database.create(
        event_checkin={
            "event": model.event,
            "attendee": attendee,
            "attended_at": UTC_NOW,
            "status": "DONE",
            "email": attendee.email,
        }
    )
    database.create(authenticate=True, profile_academy=1, role=1, capability="crud_survey")

    url = reverse_lazy("feedback:academy_event_resend_survey", kwargs={"event_id": model.event.id})
    response = client.post(
        url,
        data={"dry_run": True},
        content_type="application/json",
        HTTP_ACADEMY=1,
        HTTP_AUTHORIZATION=f"Token {model.token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["dry_run"] is True
    assert len(json["created"]) == 1
    assert json["created"][0]["scheduled"] is False
    assert Answer.objects.filter(event=model.event).count() == 0


@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.feedback.tasks.send_event_answer_email.delay", MagicMock())
def test_send_event_answer_email__delivers_email(send_email_task_mock, database, monkeypatch):
    import breathecode.notify.actions as notify_actions
    from breathecode.feedback.tasks import send_event_answer_email

    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    model = create_finished_event(database)
    setup_event_survey(model.academy)
    attendee = database.create(user=1).user
    answer = Answer.objects.create(
        event=model.event,
        user=attendee,
        academy=model.academy,
        status="SENT",
        lang="en",
        title=strings["en"]["event"]["title"],
        lowest=strings["en"]["event"]["lowest"],
        highest=strings["en"]["event"]["highest"],
    )
    token, _ = Token.get_or_create(attendee, token_type="temporal", hours_length=48)
    answer.token_id = token.id
    answer.save()

    send_event_answer_email(answer.id)

    notify_actions.send_email_message.assert_called_once()
    answer.refresh_from_db()
    assert answer.sent_at == UTC_NOW
    assert answer.status == "SENT"
