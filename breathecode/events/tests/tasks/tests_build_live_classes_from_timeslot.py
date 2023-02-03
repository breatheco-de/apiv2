import logging
from unittest.mock import MagicMock, call, patch

from breathecode.events.tasks import build_live_classes_from_timeslot
from ..mixins.new_events_tests_case import EventTestCase
from ...signals import event_saved
import breathecode.events.actions as actions


class AcademyEventTestSuite(EventTestCase):
    """
    🔽🔽🔽 with 0 CohortTimeSlot
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch.object(event_saved, 'send', MagicMock())
    def test_async_export_event_to_eventbrite__without_event(self):
        build_live_classes_from_timeslot(1)

        self.assertEqual(event_saved.send.call_args_list, [])
        self.assertEqual(self.all_event_dict(), [])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    """
    🔽🔽🔽 with 0 CohortTimeSlot
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch.object(event_saved, 'send', MagicMock())
    def test_async_export_event_to_eventbrite__without_event(self):
        model = self.bc.database.create(cohort_time_slot=1)
        build_live_classes_from_timeslot(1)

        self.assertEqual(event_saved.send.call_args_list, [])
        self.assertEqual(self.all_event_dict(), [])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
