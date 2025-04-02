import random
from unittest.mock import MagicMock, call, patch

from breathecode.admissions.models import CohortTimeSlot
from breathecode.events.models import Event  # Import Event

# TODO: Add necessary imports for models, receivers, etc.
from breathecode.events.receivers import generate_event_recap_on_finished  # Corrected receiver name
from breathecode.events.signals import event_status_updated
from breathecode.events.tasks import generate_event_recap  # Import only the relevant task to mock

from ..mixins.new_events_tests_case import EventTestCase


class GenerateEventRecapOnFinishedTestSuite(EventTestCase):
    """Tests for event_status_updated receiver that triggers generate_event_recap"""

    @patch("breathecode.events.tasks.generate_event_recap.delay")
    def test_event_status_updated_receiver__call_generate_recap_when_finished(self, generate_recap_mock):
        """Check if generate_event_recap task is called when event status changes to FINISHED"""
        event = self.bc.database.create(event=1)
        event.event.status = "FINISHED"

        generate_event_recap_on_finished(sender=None, instance=event.event, new_status="FINISHED", old_status="ACTIVE")

        self.assertEqual(generate_recap_mock.call_args_list, [call(event.event.id)])

    @patch("breathecode.events.tasks.generate_event_recap.delay")
    def test_event_status_updated_receiver__not_called_if_not_finished(self, generate_recap_mock):
        """Check if generate_event_recap task is NOT called when event status changes but not to FINISHED"""
        event = self.bc.database.create(event=1)

        statuses_to_test = ["ACTIVE", "DRAFT", "DELETED"]
        for status in statuses_to_test:
            generate_event_recap_on_finished(
                sender=None, instance=event.event, new_status=status, old_status="DRAFT"
            )  # Corrected function call
            self.assertEqual(generate_recap_mock.call_args_list, [])
            generate_recap_mock.reset_mock()  # Reset mock for the next iteration
