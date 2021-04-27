"""
Test /academy/cohort
"""
import urllib
from datetime import timedelta
from django.utils import timezone
from datetime import datetime
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_events_tests_case import EventTestCase

class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""

    def test_ical_cohorts__without_academy(self):
        """Test /academy/cohort without auth"""
        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))
        json = response.json()

        expected = {"detail":"Some academy not exist","status_code":400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ical_cohorts__without_events(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, device_id=True,
            device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__dont_get_status_deleted(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, event=True, cohort=True,
            device_id=True, cohort_kwargs=cohort_kwargs, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_one(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, cohort=True, device_id=True,
            device_id_kwargs=device_id_kwargs)
        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_one__with_incoming_true__return_zero_cohorts(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'kickoff_date': timezone.now() - timedelta(days=1)}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, cohort=True, device_id=True,
            cohort_kwargs=cohort_kwargs, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1", 'upcoming': 'true'}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_one__with_incoming_true(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'kickoff_date': timezone.now() + timedelta(days=1)}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, cohort=True, device_id=True,
            cohort_kwargs=cohort_kwargs, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1", 'upcoming': 'true'}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_one__with_teacher__with_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True, cohort=True, cohort_user=True,
            device_id=True, cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        cohort = model['cohort']
        academy = model['academy']
        user = model['user']
        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}_{key}',
            f'LOCATION:{academy.name}',
            self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_two(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(academy=True, device_id=True, skip_cohort=True,
            device_id_kwargs=device_id_kwargs)

        models = [
            self.generate_models(user=True, cohort=True, models=base),
            self.generate_models(user=True, cohort=True, models=base),
        ]

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        key = base.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_two__with_teacher__with_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(academy=True, device_id=True, skip_cohort=True,
            device_id_kwargs=device_id_kwargs)

        models = [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

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
            f'PRODID:-//BreatheCode//Academy Cohorts (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/cohorts?academy=1',
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_two__with_teacher__with_ending_date__with_two_academies_id(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}
        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base1,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base1,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]

        base2 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = models + [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base2,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base2,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]


        url = reverse_lazy('events:academy_id_ical_cohorts')
        args ={'academy': "1,2"}
        url = url + "?" + urllib.parse.urlencode(args)
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
            f'PRODID:-//BreatheCode//Academy Cohorts (1\,2) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            self.line_limit(f'URL:http://localhost:8000{url}'),
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort3.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.created_at)}',
            f'UID:breathecode_cohort_{cohort3.id}_{key}',
            f'LOCATION:{academy3.name}',
            self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort4.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.created_at)}',
            f'UID:breathecode_cohort_{cohort4.id}_{key}',
            f'LOCATION:{academy4.name}',
            self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_two__with_teacher__with_ending_date__with_two_academies_slug(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}

        device_id_kwargs = {'name': 'server'}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base1,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base1,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]

        base2 = self.generate_models(academy=True, skip_cohort=True, models=base)

        models = models + [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base2,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base2,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]

        models = sorted(models, key=lambda x: x.cohort.id)

        url = reverse_lazy('events:academy_id_ical_cohorts')
        args = {'academy_slug': ','.join(list(dict.fromkeys([x.academy.slug for x in models])))}
        url = url + "?" + urllib.parse.urlencode(args)
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
            f'PRODID:-//BreatheCode//Academy Cohorts (1\,2) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            self.line_limit(f'URL:http://localhost:8000{url}'),
            'X-WR-CALDESC:',
            f'X-WR-CALNAME:Academy - Cohorts',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}_{key}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}_{key}',
            f'LOCATION:{academy2.name}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort3.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort3.created_at)}',
            f'UID:breathecode_cohort_{cohort3.id}_{key}',
            f'LOCATION:{academy3.name}',
            self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort4.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort4.created_at)}',
            f'UID:breathecode_cohort_{cohort4.id}_{key}',
            f'LOCATION:{academy4.name}',
            self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # # this test is comment because is util to check and generate one example
    # # ical file
    # def test_generate_ical(self):
    #     """Test /academy/cohort without auth"""
    #     cohort_user_kwargs = {'role': 'TEACHER'}
    #     cohort_kwargs = {
    #         'kickoff_date': datetime.now() + timedelta(days=1, hours=12),
    #         'ending_date': datetime.now() + timedelta(days=1, hours=15),
    #     }

    #     base = self.generate_models(academy=True, skip_cohort=True)

    #     models = [
    #         self.generate_models(cohort=True, cohort_user=True, models=base,
    #             cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
    #         self.generate_models(cohort=True, cohort_user=True, models=base,
    #             cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
    #     ]

    #     url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})
    #     response = self.client.get(url)

    #     import os

    #     calendar_path = os.path.join('C:\\', 'Users', 'admin', 'desktop', 'calendar.ics')
    #     with open(calendar_path, 'w') as file:
    #         file.write(response.content.decode('utf-8').replace('\r', ''))

    #     assert False
