from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase
import breathecode.events.tasks as tasks
from django.utils import timezone

UTC_NOW = timezone.now()


class TestSyncOrgVenues(LegacyAPITestCase):
    """
    🔽🔽🔽 With zero CohortTimeSlot
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_without_timeslots(self, enable_signals):
        enable_signals()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [])

    """
    🔽🔽🔽 With invalid Cohort
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_invalid_cohort(self, enable_signals):
        enable_signals()

        cases = [
            (UTC_NOW - timedelta(seconds=random.randint(1, 1000)), False),
            (None, True),
        ]
        index = 0
        for ending_date, never_ends in cases:
            cohort = {"ending_date": ending_date, "never_ends": never_ends}
            self.bc.database.create(cohort_time_slot=1, cohort=cohort)

            self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
            self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [])
            index += 1

    """
    🔽🔽🔽 With invalid Cohort
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_right_cohort(self, enable_signals):
        enable_signals()

        ending_date = UTC_NOW + timedelta(seconds=random.randint(1, 1000))
        never_ends = False

        cohort = {"ending_date": ending_date, "never_ends": never_ends}
        cohort_time_slots = [{"cohort_id": n} for n in range(1, 3)]
        self.bc.database.create(cohort_time_slot=cohort_time_slots, cohort=(2, cohort))

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [call(1), call(2)])
