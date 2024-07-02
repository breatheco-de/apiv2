import binascii
import logging
import os
import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytz
from django.utils import timezone

import breathecode.events.actions as actions
from breathecode.events.tasks import fix_live_class_dates

from ...signals import event_saved
from ..mixins.new_events_tests_case import EventTestCase

UTC_NOW = datetime(year=2022, month=12, day=30, hour=9, minute=24, second=0, microsecond=0, tzinfo=pytz.UTC)
URANDOM = os.urandom(20)


def live_class_item(data={}):
    return {
        'id': 0,
        'cohort_time_slot_id': 0,
        'log': {},
        'remote_meeting_url': '',
        'hash': '',
        'started_at': None,
        'ended_at': None,
        'starting_at': UTC_NOW,
        'ending_at': UTC_NOW,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    # When: I call the task with 0 CohortTimeSlot
    # Then: I expect to receive an empty list of LiveClass
    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch('breathecode.admissions.signals.timeslot_saved.send_robust', MagicMock())
    def test_0_items(self):
        fix_live_class_dates.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    # When: I call the task with 1 CohortTimeSlot and Cohort ends in the past
    # Then: I expect to receive an empty list of LiveClass
    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.admissions.signals.timeslot_saved.send_robust', MagicMock())
    def test_cohort_in_the_past(self):
        cohort = {
            'never_ends': False,
            'online_meeting_url': self.bc.fake.url(),
            'kickoff_date': UTC_NOW - timedelta(seconds=random.randint(1000, 1000000)),
            'ending_date': UTC_NOW - timedelta(seconds=random.randint(1, 1000)),
        }

        starting_at = self.bc.datetime.to_datetime_integer('America/New_York', UTC_NOW - timedelta(weeks=3 * 4))

        ending_at = self.bc.datetime.to_datetime_integer('America/New_York',
                                                         UTC_NOW - timedelta(weeks=3 * 4) + timedelta(hours=3))

        cohort_time_slot = {
            'starting_at': starting_at,
            'ending_at': ending_at,
            'timezone': 'America/New_York',
            'recurrent': True,
            'recurrency_type': 'WEEKLY',
            'removed_at': None,
        }

        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort, live_class=2)

        fix_live_class_dates.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [
            self.bc.format.to_dict(model.cohort_time_slot),
        ])

        self.assertEqual(
            self.bc.database.list_of('events.LiveClass'),
            self.bc.format.to_dict(model.live_class),
        )

    """
    🔽🔽🔽 with 1 CohortTimeSlot, Cohort with ending_date in the future, it's weekly
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.admissions.signals.timeslot_saved.send_robust', MagicMock())
    def test_upcoming_cohort(self):
        cohort = {
            'never_ends': False,
            'online_meeting_url': self.bc.fake.url(),
            'kickoff_date': UTC_NOW - timedelta(weeks=2),
            'ending_date': UTC_NOW + timedelta(weeks=3) + timedelta(hours=3),
        }

        starting_at = self.bc.datetime.to_datetime_integer('America/New_York', UTC_NOW + timedelta(weeks=1))

        ending_at = self.bc.datetime.to_datetime_integer('America/New_York',
                                                         UTC_NOW + timedelta(weeks=1) + timedelta(hours=3))

        cohort_time_slot = {
            'starting_at': starting_at,
            'ending_at': ending_at,
            'timezone': 'America/New_York',
            'recurrent': True,
            'recurrency_type': 'WEEKLY',
            'removed_at': None,
        }

        live_classes = [
            {
                'starting_at': UTC_NOW + timedelta(weeks=1),
                'ending_at': UTC_NOW + timedelta(weeks=1) + timedelta(hours=3),
            },
            {
                'starting_at': UTC_NOW + timedelta(weeks=2),
                'ending_at': UTC_NOW + timedelta(weeks=2) + timedelta(hours=3),
            },
        ]
        for key in range(2):
            if bool(random.randbytes(1)):
                live_classes[key]['starting_at'] += timedelta(hours=1)
                live_classes[key]['ending_at'] += timedelta(hours=1)

            else:
                live_classes[key]['starting_at'] -= timedelta(hours=1)
                live_classes[key]['ending_at'] -= timedelta(hours=1)

        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.bc.database.create(cohort_time_slot=cohort_time_slot, cohort=cohort, live_class=live_classes)

        fix_live_class_dates.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [
            self.bc.format.to_dict(model.cohort_time_slot),
        ])

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            {
                **self.bc.format.to_dict(model.live_class[0]),
                'ending_at': datetime(2023, 1, 6, 12, 20, tzinfo=pytz.UTC),
                'starting_at': datetime(2023, 1, 6, 9, 20, tzinfo=pytz.UTC),
            },
            {
                **self.bc.format.to_dict(model.live_class[1]),
                'ending_at': datetime(2023, 1, 13, 12, 20, tzinfo=pytz.UTC),
                'starting_at': datetime(2023, 1, 13, 9, 20, tzinfo=pytz.UTC),
            },
        ])
