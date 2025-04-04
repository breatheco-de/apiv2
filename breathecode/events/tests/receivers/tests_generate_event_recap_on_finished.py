from unittest.mock import patch

import pytest

from breathecode.events.models import ACTIVE, DELETED, DRAFT, FINISHED, Event
from breathecode.events.receivers import generate_event_recap_on_finished
from breathecode.events.tasks import generate_event_recap

pytestmark = pytest.mark.django_db


@pytest.fixture
def event_factory(database):
    """Create an event for testing"""

    def _event_factory(status=ACTIVE):
        return database.create(event=1).event

    return _event_factory


@patch("breathecode.events.tasks.generate_event_recap.delay")
def test_generate_event_recap_when_finished(generate_recap_mock, event_factory):
    """Check if generate_event_recap task is called when event status is FINISHED"""
    event = event_factory()
    event.status = FINISHED

    generate_event_recap_on_finished(sender=Event, instance=event)

    generate_recap_mock.assert_called_once_with(event.id)


@patch("breathecode.events.tasks.generate_event_recap.delay")
def test_generate_event_recap_not_called_when_not_finished(generate_recap_mock, event_factory):
    """Check if generate_event_recap task is NOT called when event status is not FINISHED"""
    statuses_to_test = [ACTIVE, DRAFT, DELETED]

    for status in statuses_to_test:
        event = event_factory()
        event.status = status

        generate_event_recap_on_finished(sender=Event, instance=event)

        generate_recap_mock.assert_not_called()
        generate_recap_mock.reset_mock()
