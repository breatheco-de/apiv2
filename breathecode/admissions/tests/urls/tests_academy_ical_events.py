"""
Test /academy/cohort
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_admissions_test_case import AdmissionsTestCase

class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    def test_academy_ical_events_without_authorization(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_ical_events')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_acedemy_cohort_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_ical_events')
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_event for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_ical_events_without_events(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato')
        url = reverse_lazy('admissions:academy_ical_events')

        response = self.client.get(url)
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_events_dont_get_status_draft(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', event=True)
        url = reverse_lazy('admissions:academy_ical_events')

        response = self.client.get(url)
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_events_dont_get_status_deleted(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)

        event_kwargs = {'status': 'DELETED'}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', event=True,
            event_kwargs=event_kwargs)
        url = reverse_lazy('admissions:academy_ical_events')

        response = self.client.get(url)
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_events_with_one(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)

        event_kwargs = {'status': 'ACTIVE'}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', event=True,
            event_kwargs=event_kwargs)
        url = reverse_lazy('admissions:academy_ical_events')
        response = self.client.get(url)

        event = model['event']
        user = model['user']
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(event.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(event.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(event.created_at)}',
            f'UID:breathecode_event_{event.id}',
            self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_events_with_two(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)

        event_kwargs = {'status': 'ACTIVE'}

        base = self.generate_models(authenticate=True, profile_academy=True,
                capability='read_event', role='potato', academy=True)

        del base['user']

        models = [
            self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
                models=base),
            self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
                models=base),
        ]

        url = reverse_lazy('admissions:academy_ical_events')
        response = self.client.get(url)

        event1 = models[0]['event']
        event2 = models[1]['event']
        user1 = models[0]['user']
        user2 = models[1]['user']
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(event1.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(event1.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(event1.created_at)}',
            f'UID:breathecode_event_{event1.id}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',
            # event
            'BEGIN:VEVENT',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(event2.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(event2.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(event2.created_at)}',
            f'UID:breathecode_event_{event2.id}',
            self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
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
    #     self.headers(academy=1)

    #     from faker import Faker
    #     from datetime import datetime, timedelta

    #     fake = Faker()
    #     event_kwargs = {
    #         'status': 'ACTIVE',
    #         'title': fake.name(),
    #         'description': fake.text(),
    #         'starting_at': datetime.now() + timedelta(days=1, hours=12),
    #         'ending_at': datetime.now() + timedelta(days=1, hours=15),
    #     }

    #     base = self.generate_models(authenticate=True, profile_academy=True,
    #             capability='read_event', role='potato', academy=True)

    #     del base['user']

    #     models = [
    #         self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
    #             models=base),
    #         self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
    #             models=base),
    #     ]

    #     url = reverse_lazy('admissions:academy_ical_events')
    #     response = self.client.get(url)

    #     import os

    #     calendar_path = os.path.join('C:\\', 'Users', 'admin', 'desktop', 'calendar.ics')
    #     with open(calendar_path, 'w') as file:
    #         file.write(response.content.decode('utf-8').replace('\r', ''))

    #     assert False
