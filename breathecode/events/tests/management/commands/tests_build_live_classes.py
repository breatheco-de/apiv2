from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
from ...mixins import EventTestCase
import breathecode.events.tasks as tasks
from breathecode.events.management.commands.build_live_classes import Command
from django.utils import timezone

UTC_NOW = timezone.now()


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 With zero CohortTimeSlot
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_without_timeslots(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [])

    """
    🔽🔽🔽 With invalid Cohort
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_invalid_cohort(self):
        cases = [
            (UTC_NOW - timedelta(seconds=random.randint(1, 1000)), False),
            (None, True),
        ]
        index = 0
        for ending_date, never_ends in cases:
            cohort = {"ending_date": ending_date, "never_ends": never_ends}
            cohort_time_slots = [{"cohort_id": n + index * 2} for n in range(1, 3)]
            self.bc.database.create(cohort_time_slot=cohort_time_slots, cohort=(2, cohort))
            command = Command()
            command.handle()

            self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
            self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [])
            index += 1

    """
    🔽🔽🔽 With invalid Cohort
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_right_cohort(self):
        ending_date = UTC_NOW + timedelta(seconds=random.randint(1, 1000))
        never_ends = False

        cohort = {"ending_date": ending_date, "never_ends": never_ends}
        cohort_time_slots = [{"cohort_id": n} for n in range(1, 3)]
        self.bc.database.create(cohort_time_slot=cohort_time_slots, cohort=(2, cohort))

        tasks.build_live_classes_from_timeslot.delay.call_args_list = []

        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(tasks.build_live_classes_from_timeslot.delay.call_args_list, [call(1), call(2)])
