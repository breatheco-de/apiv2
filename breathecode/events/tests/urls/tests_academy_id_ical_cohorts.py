"""
Test /academy/cohort
"""
from datetime import datetime
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_events_tests_case import EventTestCase

class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""

    def test_academy_ical_cohorts_without_events(self):
        """Test /academy/cohort without auth"""
        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})

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

    def test_academy_ical_cohorts_dont_get_status_deleted(self):
        """Test /academy/cohort without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        model = self.generate_models(academy=True, event=True, cohort=True,
            cohort_kwargs=cohort_kwargs)
        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})

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

    def test_academy_ical_cohorts_with_one(self):
        """Test /academy/cohort without auth"""
        model = self.generate_models(academy=True, cohort=True)
        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})
        response = self.client.get(url)

        cohort = model['cohort']
        academy = model['academy']
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}',
            f'LOCATION:{academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_cohorts_with_one_with_teacher_and_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}
        model = self.generate_models(academy=True, cohort=True, cohort_user=True,
            cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs)
        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})
        response = self.client.get(url)

        cohort = model['cohort']
        academy = model['academy']
        user = model['user']
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort.created_at)}',
            f'UID:breathecode_cohort_{cohort.id}',
            f'LOCATION:{academy.name}',
            self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_cohorts_with_two(self):
        """Test /academy/cohort without auth"""
        base = self.generate_models(academy=True, skip_cohort=True)

        models = [
            self.generate_models(user=True, cohort=True, models=base),
            self.generate_models(user=True, cohort=True, models=base),
        ]

        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})
        response = self.client.get(url)

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}',
            f'LOCATION:{academy1.name}',
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}',
            f'LOCATION:{academy2.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_academy_ical_cohorts_with_two_with_teacher_and_ending_date(self):
        """Test /academy/cohort without auth"""
        cohort_user_kwargs = {'role': 'TEACHER'}
        cohort_kwargs = {'ending_date': datetime.now()}
        base = self.generate_models(academy=True, skip_cohort=True)

        models = [
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
            self.generate_models(user=True, cohort=True, cohort_user=True, models=base,
                cohort_kwargs=cohort_kwargs, cohort_user_kwargs=cohort_user_kwargs),
        ]

        url = reverse_lazy('events:academy_id_ical_cohorts', kwargs={'academy_id': 1})
        response = self.client.get(url)

        cohort1 = models[0]['cohort']
        cohort2 = models[1]['cohort']
        academy1 = models[0]['academy']
        academy2 = models[1]['academy']
        user1 = models[0]['user']
        user2 = models[1]['user']

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//4Geeks Academy//4Geeks events//',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort1.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort1.created_at)}',
            f'UID:breathecode_cohort_{cohort1.id}',
            f'LOCATION:{academy1.name}',
            self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
            'END:VEVENT',
            'BEGIN:VEVENT',
            f'SUMMARY:{cohort2.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.kickoff_date)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.ending_date)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(cohort2.created_at)}',
            f'UID:breathecode_cohort_{cohort2.id}',
            f'LOCATION:{academy2.name}',
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
