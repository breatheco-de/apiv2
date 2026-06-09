from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.events.models import FINISHED, Event

pytestmark = pytest.mark.django_db


@pytest.fixture
def event_factory(database):
    def _event_factory(**event_kwargs):
        return database.create(event=1, event_kwargs=event_kwargs).event

    return _event_factory


@patch("breathecode.events.tasks.send_event_recording_notification.delay")
def test_queues_notification_when_recording_first_set_on_finished_event(notification_mock, event_factory):
    event = event_factory(
        status=FINISHED,
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url=None,
    )

    event.recording_url = "https://example.com/recording"
    event.save()

    notification_mock.assert_called_once_with(event.id)


@patch("breathecode.events.tasks.send_event_recording_notification.delay")
def test_does_not_queue_when_event_not_finished(notification_mock, event_factory):
    event = event_factory(
        status="ACTIVE",
        ending_at=timezone.now() + timedelta(hours=2),
        recording_url=None,
    )

    event.recording_url = "https://example.com/recording"
    event.save()

    notification_mock.assert_not_called()


@patch("breathecode.events.tasks.send_event_recording_notification.delay")
def test_does_not_queue_when_recording_url_updated(notification_mock, event_factory):
    event = event_factory(
        status=FINISHED,
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url="https://example.com/old-recording",
    )

    event.recording_url = "https://example.com/new-recording"
    event.save()

    notification_mock.assert_not_called()


@patch("breathecode.events.tasks.send_event_recording_notification.delay")
def test_queues_when_ending_at_passed_even_if_status_active(notification_mock, event_factory):
    event = event_factory(
        status="ACTIVE",
        ending_at=timezone.now() - timedelta(hours=1),
        recording_url=None,
    )

    event.recording_url = "https://example.com/recording"
    event.save()

    notification_mock.assert_called_once_with(event.id)
