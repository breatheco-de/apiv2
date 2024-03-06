"""
Test /academy/cohort
"""
import urllib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz
from dateutil.tz import gettz
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.events.actions import fix_datetime_weekday
from breathecode.utils import DatetimeInteger

from ..mixins.new_events_tests_case import EventTestCase


class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__without_academy(self):
        """Test /academy/cohort without auth"""
        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))
        json = response.json()

        expected = {'detail': 'Some academy not exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__without_events(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, skip_cohort=True, device_id=True, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__dont_get_status_deleted(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     cohort=True,
                                     device_id=True,
                                     cohort_kwargs=cohort_kwargs,
                                     device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort = {
            'ending_date': timezone.now() + timedelta(weeks=10 * 52),
            'kickoff_date': datetime.today().isoformat()
        }
        model = self.generate_models(academy=True, cohort=cohort, device_id=True, device_id_kwargs=device_id_kwargs)
        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__ending_date_is_none(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=1, cohort=1, device_id=1, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__never_ends_true(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort = {'never_ends': True}
        model = self.generate_models(academy=1, cohort=cohort, device_id=1, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__with_incoming_true__return_zero_cohorts(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'kickoff_date': timezone.now() - timedelta(days=1)}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     cohort=True,
                                     device_id=True,
                                     cohort_kwargs=cohort_kwargs,
                                     device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1', 'upcoming': 'true'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__with_incoming_true(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {
            'kickoff_date': timezone.now() + timedelta(days=1),
            'ending_date': timezone.now() + timedelta(weeks=10 * 52),
        }
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     cohort=True,
                                     device_id=True,
                                     cohort_kwargs=cohort_kwargs,
                                     device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1', 'upcoming': 'true'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__with_teacher__with_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': timezone.now()}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     cohort={'kickoff_date': datetime.today().isoformat()},
                                     cohort_user=True,
                                     device_id=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        user = model['user']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(academy=True, device_id=True, skip_cohort=True, device_id_kwargs=device_id_kwargs)

        cohort = {
            'kickoff_date': datetime.today().isoformat(),
            'ending_date': timezone.now() + timedelta(weeks=10 * 52)
        }
        models = [
            self.generate_models(user=True, cohort=cohort, models=base),
            self.generate_models(user=True, cohort=cohort, models=base),
        ]

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        key = base.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two__with_teacher__with_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': timezone.now()}
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(academy=True, device_id=True, skip_cohort=True, device_id_kwargs=device_id_kwargs)

        models = [
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
        ]

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        user1 = models[0]['user']
        user2 = models[1]['user']
        key = base.device_id.key

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two__with_teacher__with_ending_date__with_two_academies_id(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': timezone.now()}
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = [
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base1,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base1,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
        ]

        base2 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = models + [
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base2,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base2,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
        ]

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1,2'}
        url = url + '?' + urllib.parse.urlencode(args)
        response = self.client.get(url)

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        cohort3 = models[2]['cohort']
        cohort4 = models[3]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        academy3 = models[2]['academy']
        academy4 = models[3]['academy']
        user1 = models[0]['user']
        user2 = models[1]['user']
        user3 = models[2]['user']
        user4 = models[3]['user']
        key = base.device_id.key
        url = url.replace('%2C', ',')

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1\\,2) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            self.line_limit(f'URL:http://localhost:8000{url}'),
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort3.name}',
            f'DTSTART:{self.datetime_to_ical(cohort3.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort3.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort3.created_at)}',
            f'UID:breathecode_cohort_{cohort3.id}_{key}',
            f'LOCATION:{academy3.name}',
            self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort4.name}',
            f'DTSTART:{self.datetime_to_ical(cohort4.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort4.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort4.created_at)}',
            f'UID:breathecode_cohort_{cohort4.id}_{key}',
            f'LOCATION:{academy4.name}',
            self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two__with_teacher__with_ending_date__with_two_academies_slug(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': timezone.now()}

        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = [
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base1,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base1,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
        ]

        base2 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = models + [
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base2,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True,
                                 cohort={'kickoff_date': datetime.today().isoformat()},
                                 cohort_user=True,
                                 models=base2,
                                 cohort_kwargs=cohort_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs),
        ]

        models = sorted(models, key=lambda x: x.cohort.id)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy_slug': ','.join(list(dict.fromkeys([x.academy.slug for x in models])))}
        url = url + '?' + urllib.parse.urlencode(args)
        response = self.client.get(url)

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        cohort3 = models[2]['cohort']
        cohort4 = models[3]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        academy3 = models[2]['academy']
        academy4 = models[3]['academy']
        user1 = models[0]['user']
        user2 = models[1]['user']
        user3 = models[2]['user']
        user4 = models[3]['user']
        key = base.device_id.key
        url = url.replace('%2C', ',')

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1\\,2) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            self.line_limit(f'URL:http://localhost:8000{url}'),
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort3.name}',
            f'DTSTART:{self.datetime_to_ical(cohort3.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort3.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort3.created_at)}',
            f'UID:breathecode_cohort_{cohort3.id}_{key}',
            f'LOCATION:{academy3.name}',
            self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
            'END:VEVENT',

            # =================================================================
            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort4.name}',
            f'DTSTART:{self.datetime_to_ical(cohort4.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort4.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort4.created_at)}',
            f'UID:breathecode_cohort_{cohort4.id}_{key}',
            f'LOCATION:{academy4.name}',
            self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 With first cohort day and last cohort day
    """

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__first_day__last_day(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'kickoff_date': datetime(year=2029, month=1, day=10, tzinfo=pytz.timezone('UTC')),
            'ending_date': datetime(year=2030, month=10, day=10, tzinfo=pytz.timezone('UTC')),
        }

        starting_datetime_integer = 202810080030
        ending_datetime_integer = 202810080630
        cohort_time_slot_kwargs = {
            'timezone': 'Europe/Madrid',
            'starting_at': starting_datetime_integer,
            'ending_at': ending_datetime_integer,
        }

        model = self.generate_models(academy=True,
                                     cohort=True,
                                     device_id=True,
                                     cohort_time_slot=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort = model['cohort']
        timeslot = model['cohort_time_slot']
        academy = model['academy']
        last_timeslot_starting_at = datetime(year=2030,
                                             month=10,
                                             day=6,
                                             hour=0,
                                             minute=30,
                                             tzinfo=gettz('Europe/Madrid'))

        last_timeslot_ending_at = datetime(year=2030, month=10, day=6, hour=6, minute=30, tzinfo=gettz('Europe/Madrid'))
        key = model.device_id.key

        starting_at = DatetimeInteger.to_datetime(model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at)

        starting_at_fixed = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                                       starting_at,
                                                                       next=True),
                                                  utc=False)

        ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)

        ending_at_fixed = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date, ending_at, next=True),
                                                utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{starting_at_fixed}',
            f'DTEND;TZID=Europe/Madrid:{ending_at_fixed}',
            f'DTSTAMP:{self.datetime_to_ical(timeslot.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_first_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{self.datetime_to_ical(last_timeslot_starting_at, utc=False)}',
            f'DTEND;TZID=Europe/Madrid:{self.datetime_to_ical(last_timeslot_ending_at, utc=False)}',
            f'DTSTAMP:{self.datetime_to_ical(timeslot.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_last_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_one__first_day__last_day__timeslot_not_recurrent(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'kickoff_date': datetime(year=2020, month=10, day=10, tzinfo=pytz.timezone('UTC')),
            'ending_date': datetime(year=2030, month=10, day=10, tzinfo=pytz.timezone('UTC')),
        }

        starting_datetime_integer = 202510080030
        ending_datetime_integer = 202510080630
        cohort_time_slot_kwargs = {
            'starting_at': starting_datetime_integer,
            'ending_at': ending_datetime_integer,
            'timezone': 'Europe/Madrid',
            'recurrent': False,
        }

        model = self.generate_models(academy=True,
                                     cohort=True,
                                     device_id=True,
                                     cohort_time_slot=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort = model['cohort']
        timeslot = model['cohort_time_slot']
        academy = model['academy']
        key = model.device_id.key

        starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
        first_timeslot_starting_at = self.datetime_to_ical(starting_at, utc=False)

        last_timeslot_starting_at = self.datetime_to_ical(starting_at, utc=False)

        ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
        first_timeslot_ending_at = self.datetime_to_ical(ending_at, utc=False)

        last_timeslot_ending_at = self.datetime_to_ical(ending_at, utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{first_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{first_timeslot_ending_at}',
            f'DTSTAMP:{self.datetime_to_ical(timeslot.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_first_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{last_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{last_timeslot_ending_at}',
            f'DTSTAMP:{self.datetime_to_ical(timeslot.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_last_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two__first_day__last_day__two_timeslots(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'kickoff_date': datetime(year=2020, month=10, day=10, tzinfo=pytz.timezone('UTC')),
            'ending_date': datetime(year=2030, month=10, day=10, tzinfo=pytz.timezone('UTC')),
        }

        first_cohort_time_slot_kwargs = {
            'timezone': 'Europe/Madrid',
            'starting_at': 202110080030,
            'ending_at': 202110080630,
        }

        last_cohort_time_slot_kwargs = {
            'timezone': 'Europe/Madrid',
            'starting_at': 202810080030,
            'ending_at': 202810080630,
        }

        cohort_time_slots = [
            {
                **first_cohort_time_slot_kwargs,
                'cohort_id': 1,
            },
            {
                **last_cohort_time_slot_kwargs,
                'cohort_id': 1,
            },
            {
                **first_cohort_time_slot_kwargs,
                'cohort_id': 2,
            },
            {
                **last_cohort_time_slot_kwargs,
                'cohort_id': 2,
            },
        ]
        model = self.generate_models(academy=True,
                                     cohort=(2, cohort_kwargs),
                                     device_id=device_id_kwargs,
                                     cohort_time_slot=cohort_time_slots)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort1 = model.cohort[0]
        cohort2 = model.cohort[1]

        academy = model.academy
        timeslot1 = model.cohort_time_slot[0]
        timeslot2 = model.cohort_time_slot[1]
        timeslot3 = model.cohort_time_slot[2]
        # timeslot4 = model.cohort_time_slot[3]
        key = model.device_id.key

        starting_at1 = self.datetime_to_ical(model.cohort[0].kickoff_date)
        starting_at2 = self.datetime_to_ical(model.cohort[1].kickoff_date)

        starting_at_utc1 = self.datetime_to_ical(model.cohort[0].created_at)
        starting_at_utc2 = self.datetime_to_ical(model.cohort[1].created_at)

        ending_at1 = self.datetime_to_ical(model.cohort[0].ending_date)
        ending_at2 = self.datetime_to_ical(model.cohort[1].ending_date)

        first_timeslot_starting_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].kickoff_date,
            DatetimeInteger.to_datetime(timeslot1.timezone, first_cohort_time_slot_kwargs['starting_at']),
            next=True),
                                                           utc=False)

        first_timeslot_starting_at_utc1 = self.datetime_to_ical(timeslot1.created_at, utc=True)
        first_timeslot_starting_at_utc2 = self.datetime_to_ical(timeslot3.created_at, utc=True)

        first_timeslot_ending_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].kickoff_date,
            DatetimeInteger.to_datetime(timeslot1.timezone, first_cohort_time_slot_kwargs['ending_at']),
            next=True),
                                                         utc=False)

        last_timeslot_starting_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].ending_date,
            DatetimeInteger.to_datetime(timeslot2.timezone, last_cohort_time_slot_kwargs['starting_at']),
            prev=True),
                                                          utc=False)

        last_timeslot_starting_at_utc = self.datetime_to_ical(timeslot2.cohort.created_at, utc=True)

        last_timeslot_ending_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[1].ending_date,
            DatetimeInteger.to_datetime(timeslot2.timezone, last_cohort_time_slot_kwargs['ending_at']),
            prev=True),
                                                        utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{first_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{first_timeslot_ending_at}',
            f'DTSTAMP:{first_timeslot_starting_at_utc1}',
            f'UID:breathecode_cohort_{cohort1.id}_first_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{starting_at1}',
            f'DTEND:{ending_at1}',
            f'DTSTAMP:{starting_at_utc1}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{last_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{last_timeslot_ending_at}',
            f'DTSTAMP:{last_timeslot_starting_at_utc}',
            f'UID:breathecode_cohort_{cohort1.id}_last_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{first_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{first_timeslot_ending_at}',
            f'DTSTAMP:{first_timeslot_starting_at_utc2}',
            f'UID:breathecode_cohort_{cohort2.id}_first_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{starting_at2}',
            f'DTEND:{ending_at2}',
            f'DTSTAMP:{starting_at_utc2}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{last_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{last_timeslot_ending_at}',
            f'DTSTAMP:{last_timeslot_starting_at_utc}',
            f'UID:breathecode_cohort_{cohort2.id}_last_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('breathecode.events.tasks.build_live_classes_from_timeslot.delay', MagicMock())
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_ical_cohorts__with_two__first_day__last_day__two_timeslots__cohort_with_meeting_url(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = [{
            'online_meeting_url': self.bc.fake.url(),
            'kickoff_date': datetime(year=2020, month=10, day=10, tzinfo=pytz.timezone('UTC')),
            'ending_date': datetime(year=2030, month=10, day=10, tzinfo=pytz.timezone('UTC')),
        } for _ in range(0, 2)]

        first_cohort_time_slot_kwargs = {
            'timezone': 'Europe/Madrid',
            'starting_at': 202110080030,
            'ending_at': 202110080630,
        }

        last_cohort_time_slot_kwargs = {
            'timezone': 'Europe/Madrid',
            'starting_at': 202810080030,
            'ending_at': 202810080630,
        }

        cohort_time_slots = [
            {
                **first_cohort_time_slot_kwargs,
                'cohort_id': 1,
            },
            {
                **last_cohort_time_slot_kwargs,
                'cohort_id': 1,
            },
            {
                **first_cohort_time_slot_kwargs,
                'cohort_id': 2,
            },
            {
                **last_cohort_time_slot_kwargs,
                'cohort_id': 2,
            },
        ]
        model = self.generate_models(academy=True,
                                     cohort=cohort_kwargs,
                                     device_id=device_id_kwargs,
                                     cohort_time_slot=cohort_time_slots)

        url = reverse_lazy('events:ical_cohorts')
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        cohort1 = model.cohort[0]
        cohort2 = model.cohort[1]

        timeslot1 = model.cohort_time_slot[0]
        timeslot2 = model.cohort_time_slot[1]
        timeslot3 = model.cohort_time_slot[2]
        # timeslot4 = model.cohort_time_slot[3]
        key = model.device_id.key

        starting_at1 = self.datetime_to_ical(model.cohort[0].kickoff_date)
        starting_at2 = self.datetime_to_ical(model.cohort[1].kickoff_date)

        starting_at_utc1 = self.datetime_to_ical(model.cohort[0].created_at)
        starting_at_utc2 = self.datetime_to_ical(model.cohort[1].created_at)

        ending_at1 = self.datetime_to_ical(model.cohort[0].ending_date)
        ending_at2 = self.datetime_to_ical(model.cohort[1].ending_date)

        first_timeslot_starting_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].kickoff_date,
            DatetimeInteger.to_datetime(timeslot1.timezone, first_cohort_time_slot_kwargs['starting_at']),
            next=True),
                                                           utc=False)

        first_timeslot_starting_at_utc1 = self.datetime_to_ical(timeslot1.created_at, utc=True)
        first_timeslot_starting_at_utc2 = self.datetime_to_ical(timeslot3.created_at, utc=True)

        first_timeslot_ending_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].kickoff_date,
            DatetimeInteger.to_datetime(timeslot1.timezone, first_cohort_time_slot_kwargs['ending_at']),
            next=True),
                                                         utc=False)

        last_timeslot_starting_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[0].ending_date,
            DatetimeInteger.to_datetime(timeslot2.timezone, last_cohort_time_slot_kwargs['starting_at']),
            prev=True),
                                                          utc=False)

        last_timeslot_starting_at_utc = self.datetime_to_ical(timeslot2.cohort.created_at, utc=True)

        last_timeslot_ending_at = self.datetime_to_ical(fix_datetime_weekday(
            model.cohort[1].ending_date,
            DatetimeInteger.to_datetime(timeslot2.timezone, last_cohort_time_slot_kwargs['ending_at']),
            prev=True),
                                                        utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//4Geeks//Academy Cohorts (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{first_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{first_timeslot_ending_at}',
            f'DTSTAMP:{first_timeslot_starting_at_utc1}',
            f'UID:breathecode_cohort_{cohort1.id}_first_{key}',
            f'LOCATION:{cohort_kwargs[0]["online_meeting_url"]}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART:{starting_at1}',
            f'DTEND:{ending_at1}',
            f'DTSTAMP:{starting_at_utc1}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{cohort_kwargs[0]["online_meeting_url"]}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{last_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{last_timeslot_ending_at}',
            f'DTSTAMP:{last_timeslot_starting_at_utc}',
            f'UID:breathecode_cohort_{cohort1.id}_last_{key}',
            f'LOCATION:{cohort_kwargs[0]["online_meeting_url"]}',
            'END:VEVENT',

            # =================================================================
            # First event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name} - First day',
            f'DTSTART;TZID=Europe/Madrid:{first_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{first_timeslot_ending_at}',
            f'DTSTAMP:{first_timeslot_starting_at_utc2}',
            f'UID:breathecode_cohort_{cohort2.id}_first_{key}',
            f'LOCATION:{cohort_kwargs[1]["online_meeting_url"]}',
            'END:VEVENT',

            # Event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART:{starting_at2}',
            f'DTEND:{ending_at2}',
            f'DTSTAMP:{starting_at_utc2}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{cohort_kwargs[1]["online_meeting_url"]}',
            'END:VEVENT',

            # Last event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name} - Last day',
            f'DTSTART;TZID=Europe/Madrid:{last_timeslot_starting_at}',
            f'DTEND;TZID=Europe/Madrid:{last_timeslot_ending_at}',
            f'DTSTAMP:{last_timeslot_starting_at_utc}',
            f'UID:breathecode_cohort_{cohort2.id}_last_{key}',
            f'LOCATION:{cohort_kwargs[1]["online_meeting_url"]}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
