from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

from breathecode.events.models import FINISHED
from breathecode.events.tasks import send_event_recording_notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def event_factory(database):
    def _event_factory(**event_kwargs):
        return database.create(event=1, event_kwargs=event_kwargs).event

    return _event_factory


@patch("task_manager.core.decorators.logger.error")
def test_event_not_found(logger_error_mock):
    send_event_recording_notification(event_id=999)

    logger_error_mock.assert_called_once_with("Event 999 not found. Task cannot continue.", exc_info=True)


def test_aborts_when_event_has_no_recording_url(event_factory):
    event = event_factory(
        status=FINISHED,
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url=None,
    )

    with pytest.raises(AbortTask, match="has no recording URL"):
        send_event_recording_notification(event_id=event.id)


def test_aborts_when_event_not_finished(event_factory):
    event = event_factory(
        status="ACTIVE",
        ending_at=timezone.now() + timedelta(hours=2),
        recording_url="https://example.com/recording",
    )

    with pytest.raises(AbortTask, match="has not finished yet"):
        send_event_recording_notification(event_id=event.id)


@patch("breathecode.events.tasks.notify_actions.send_email_message", MagicMock(return_value=True))
def test_sends_email_to_attended_checkins_only(send_email_mock, event_factory, database):
    event = event_factory(
        status=FINISHED,
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url="https://example.com/recording",
        lang="en",
    )
    database.create(
        event_checkin=[
            {
                "event": event,
                "email": "attended@example.com",
                "status": "DONE",
                "attended_at": timezone.now() - timedelta(minutes=30),
            },
            {
                "event": event,
                "email": "rsvp@example.com",
                "status": "PENDING",
                "attended_at": None,
            },
        ]
    )

    send_event_recording_notification(event_id=event.id)

    send_email_mock.assert_called_once()
    assert send_email_mock.call_args[0][1] == "attended@example.com"
    assert send_email_mock.call_args[0][2]["LINK"] == "https://example.com/recording"


@patch("breathecode.events.tasks.notify_actions.send_email_message", MagicMock(return_value=True))
def test_no_emails_when_no_attended_checkins(send_email_mock, event_factory):
    event = event_factory(
        status=FINISHED,
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url="https://example.com/recording",
    )

    send_event_recording_notification(event_id=event.id)

    send_email_mock.assert_not_called()
