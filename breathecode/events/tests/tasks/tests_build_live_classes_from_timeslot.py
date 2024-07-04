from datetime import timedelta, datetime
import logging
import os
import pytz
from unittest.mock import MagicMock, call, patch

from breathecode.events.tasks import build_live_classes_from_timeslot
from ..mixins.new_events_tests_case import EventTestCase
import breathecode.events.actions as actions
from django.utils import timezone
from breathecode.events.models import LiveClass

UTC_NOW = timezone.now()
DATE = datetime(year=2022, month=12, day=30, hour=9, minute=24, second=0, microsecond=0, tzinfo=pytz.UTC)
URANDOM = os.urandom(16)


def live_class_item(data={}):
    return {
        "id": 0,
        "cohort_time_slot_id": 0,
        "log": {},
        "remote_meeting_url": "",
        "hash": "",
        "started_at": None,
        "ended_at": None,
        "starting_at": UTC_NOW,
        "ending_at": UTC_NOW,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    """
    🔽🔽🔽 with 0 CohortTimeSlot
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    def test_zero_cohort_time_slots(self):
        build_live_classes_from_timeslot(1)

        self.assertEqual(self.bc.database.list_of("admissions.CohortTimeSlot"), [])
        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort never ends
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    def test_one_cohort_time_slot_with_cohort_never_ends(self):
        cohort = {"never_ends": True, "ending_date": None}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(cohort_time_slot=1, cohort=cohort)

        build_live_classes_from_timeslot(1)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortTimeSlot"),
            [
                self.bc.format.to_dict(model.cohort_time_slot),
            ],
        )
        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort with ending_date in the past
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=DATE))
    def test_one_cohort_time_slot_with_ending_date_in_the_past(self):
        base_date = DATE
        cohort = {
            "never_ends": False,
            "ending_date": base_date - timedelta(weeks=3 * 5),
            "online_meeting_url": self.bc.fake.url(),
            "kickoff_date": base_date - timedelta(weeks=3 * 10),
        }

        starting_at = self.bc.datetime.to_datetime_integer("America/New_York", base_date - timedelta(weeks=3 * 4))

        ending_at = self.bc.datetime.to_datetime_integer(
            "America/New_York", base_date - timedelta(weeks=3 * 4) + timedelta(hours=3)
        )

        cohort_time_slot = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "timezone": "America/New_York",
            "recurrent": True,
            "recurrency_type": "WEEKLY",
            "removed_at": None,
        }

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort)

        build_live_classes_from_timeslot(1)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortTimeSlot"),
            [
                self.bc.format.to_dict(model.cohort_time_slot),
            ],
        )
        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort with ending_date in the future, it's weekly
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=DATE))
    @patch(
        "breathecode.events.models.LiveClass._get_hash",
        MagicMock(
            side_effect=[
                "r1",
                "r2",
                "r3",
                "r4",
                "r5",
                "r6",
            ]
        ),
    )
    def test_one_cohort_time_slot_with_ending_date_in_the_future__weekly(self):
        base_date = DATE
        cohort = {
            "never_ends": False,
            "ending_date": base_date,
            "online_meeting_url": self.bc.fake.url(),
            "kickoff_date": base_date - timedelta(weeks=3 * 2),
        }

        starting_at = self.bc.datetime.to_datetime_integer("America/New_York", base_date - timedelta(weeks=3 * 4))

        ending_at = self.bc.datetime.to_datetime_integer(
            "America/New_York", base_date - timedelta(weeks=3 * 4) + timedelta(hours=3)
        )

        cohort_time_slot = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "timezone": "America/New_York",
            "recurrent": True,
            "recurrency_type": "WEEKLY",
            "removed_at": None,
        }

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort)

        build_live_classes_from_timeslot(1)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortTimeSlot"),
            [
                self.bc.format.to_dict(model.cohort_time_slot),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                live_class_item(
                    {
                        "id": 1,
                        "cohort_time_slot_id": 1,
                        "hash": "r1",
                        "starting_at": datetime(2022, 11, 18, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 11, 18, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 2,
                        "cohort_time_slot_id": 1,
                        "hash": "r2",
                        "starting_at": datetime(2022, 11, 25, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 11, 25, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 3,
                        "cohort_time_slot_id": 1,
                        "hash": "r3",
                        "starting_at": datetime(2022, 12, 2, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 2, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 4,
                        "cohort_time_slot_id": 1,
                        "hash": "r4",
                        "starting_at": datetime(2022, 12, 9, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 9, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 5,
                        "cohort_time_slot_id": 1,
                        "hash": "r5",
                        "starting_at": datetime(2022, 12, 16, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 16, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 6,
                        "cohort_time_slot_id": 1,
                        "hash": "r6",
                        "starting_at": datetime(2022, 12, 23, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 23, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
            ],
        )
        assert LiveClass._get_hash.call_args_list == [call() for _ in range(6)]

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort with ending_date in the future, it's weekly
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=DATE))
    @patch(
        "breathecode.events.models.LiveClass._get_hash",
        MagicMock(
            side_effect=[
                "r1",
                "r2",
                "r3",
                "r4",
                "r5",
                "r6",
            ]
        ),
    )
    def test_one_cohort_time_slot_with_ending_date_in_the_future__monthly(self):
        base_date = DATE
        cohort = {
            "never_ends": False,
            "ending_date": base_date,
            "online_meeting_url": self.bc.fake.url(),
            "kickoff_date": base_date - timedelta(weeks=3 * 2),
        }

        starting_at = self.bc.datetime.to_datetime_integer("America/New_York", base_date - timedelta(weeks=3 * 4))

        ending_at = self.bc.datetime.to_datetime_integer(
            "America/New_York", base_date - timedelta(weeks=3 * 4) + timedelta(hours=3)
        )

        cohort_time_slot = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "timezone": "America/New_York",
            "recurrent": True,
            "recurrency_type": "MONTHLY",
            "removed_at": None,
        }

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort)

        build_live_classes_from_timeslot(1)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortTimeSlot"),
            [
                self.bc.format.to_dict(model.cohort_time_slot),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                live_class_item(
                    {
                        "id": 1,
                        "cohort_time_slot_id": 1,
                        "hash": "r1",
                        "starting_at": datetime(2022, 12, 7, 10, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 7, 13, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
            ],
        )
        assert LiveClass._get_hash.call_args_list == [call()]

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort with ending_date in the future, it's daily
    """

    @patch.object(actions, "export_event_to_eventbrite", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(logging.Logger, "debug", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=DATE))
    @patch(
        "breathecode.events.models.LiveClass._get_hash",
        MagicMock(
            side_effect=[
                "r1",
                "r2",
                "r3",
                "r4",
                "r5",
                "r6",
            ]
        ),
    )
    def test_one_cohort_time_slot_with_ending_date_in_the_future__daily(self):
        base_date = DATE
        cohort = {
            "never_ends": False,
            "ending_date": base_date,
            "online_meeting_url": self.bc.fake.url(),
            "kickoff_date": base_date - timedelta(weeks=1),
        }

        starting_at = self.bc.datetime.to_datetime_integer("America/New_York", base_date - timedelta(weeks=2))

        ending_at = self.bc.datetime.to_datetime_integer(
            "America/New_York", base_date - timedelta(weeks=2) + timedelta(hours=3)
        )

        cohort_time_slot = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "timezone": "America/New_York",
            "recurrent": True,
            "recurrency_type": "DAILY",
            "removed_at": None,
        }

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort)

        build_live_classes_from_timeslot(1)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortTimeSlot"),
            [
                self.bc.format.to_dict(model.cohort_time_slot),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                live_class_item(
                    {
                        "id": 1,
                        "cohort_time_slot_id": 1,
                        "hash": "r1",
                        "starting_at": datetime(2022, 12, 24, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 24, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 2,
                        "cohort_time_slot_id": 1,
                        "hash": "r2",
                        "starting_at": datetime(2022, 12, 25, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 25, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 3,
                        "cohort_time_slot_id": 1,
                        "hash": "r3",
                        "starting_at": datetime(2022, 12, 26, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 26, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 4,
                        "cohort_time_slot_id": 1,
                        "hash": "r4",
                        "starting_at": datetime(2022, 12, 27, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 27, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 5,
                        "cohort_time_slot_id": 1,
                        "hash": "r5",
                        "starting_at": datetime(2022, 12, 28, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 28, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
                live_class_item(
                    {
                        "id": 6,
                        "cohort_time_slot_id": 1,
                        "hash": "r6",
                        "starting_at": datetime(2022, 12, 29, 9, 20, tzinfo=pytz.UTC),
                        "ending_at": datetime(2022, 12, 29, 12, 20, tzinfo=pytz.UTC),
                        "remote_meeting_url": model.cohort.online_meeting_url,
                    }
                ),
            ],
        )
        assert LiveClass._get_hash.call_args_list == [call() for _ in range(6)]
