"""
Test /academy/cohort
"""
from datetime import datetime, timedelta
import urllib
from django.urls.base import reverse_lazy
import pytz
from rest_framework import status
from breathecode.events.actions import fix_datetime_weekday

from breathecode.utils.datetime_interger import DatetimeInteger
from ..mixins.new_events_tests_case import EventTestCase


class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""
    """
    🔽🔽🔽 Without student
    """

    def test_ical_cohorts__without_student(self):
        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'academy': '1'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))
        json = response.json()

        expected = {
            'detail': 'student-not-exist',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Without time slot
    """

    def test_ical_cohorts__without_cohort_time_slot(self):
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot and the Cohort never ends
    """

    def test_ical_cohorts__with_one__cohort_never_ends(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0),
            'never_ends': True,
        }

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=device_id_kwargs,
                                     cohort_user=1,
                                     cohort_time_slot=cohort_time_slot_kwargs,
                                     cohort=cohort_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot and the Cohort with ending_date as None
    """

    def test_ical_cohorts__with_one__cohort_without_ending_date(self):
        device_id_kwargs = {'name': 'server'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=device_id_kwargs,
                                     cohort_user=1,
                                     cohort_time_slot=cohort_time_slot_kwargs,
                                     cohort=1)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot with ending_date in Cohort
    """

    def test_ical_cohorts__with_one__with_ending_date(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        starting_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                                 DatetimeInteger.to_datetime(
                                                                     model.cohort_time_slot.timezone,
                                                                     model.cohort_time_slot.starting_at),
                                                                 next=True),
                                            utc=False)

        starting_at_utc = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at),
                                                utc=True)

        ending_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                               DatetimeInteger.to_datetime(
                                                                   model.cohort_time_slot.timezone,
                                                                   model.cohort_time_slot.ending_at),
                                                               next=True),
                                          utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model.academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot it's not recurrent
    """

    def test_ical_cohorts__with_one__not_recurrent(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
            'recurrent': False,
        }
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        starting_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                                 DatetimeInteger.to_datetime(
                                                                     model.cohort_time_slot.timezone,
                                                                     model.cohort_time_slot.starting_at),
                                                                 next=True),
                                            utc=False)

        starting_at_utc = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at),
                                                utc=True)

        ending_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                               DatetimeInteger.to_datetime(
                                                                   model.cohort_time_slot.timezone,
                                                                   model.cohort_time_slot.ending_at),
                                                               next=True),
                                          utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'LOCATION:{model.academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot without cohort ending date
    """

    def test_ical_cohorts__with_one__without_ending_date(self):
        device_id_kwargs = {'name': 'server'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        starting_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                                 DatetimeInteger.to_datetime(
                                                                     model.cohort_time_slot.timezone,
                                                                     model.cohort_time_slot.starting_at),
                                                                 next=True),
                                            utc=False)

        created_at = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at),
                                           utc=True)

        ending_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                               DatetimeInteger.to_datetime(
                                                                   model.cohort_time_slot.timezone,
                                                                   model.cohort_time_slot.ending_at),
                                                               next=True),
                                          utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot with cohort stage deleted
    """

    def test_ical_cohorts__with_one__stage_deleted(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {'stage': 'DELETED'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot with incoming true in querystring
    """

    def test_ical_cohorts__with_one__with_incoming_true__return_zero_time_slots(self):
        device_id_kwargs = {'name': 'server'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'upcoming': 'true'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_cohorts__with_one__with_incoming_true(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'kickoff_date':
            datetime.now() + timedelta(days=2),
            'ending_date':
            datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0, tzinfo=pytz.timezone('UTC')),
        }

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_time_slot_kwargs=cohort_time_slot_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'upcoming': 'true'}
        response = self.client.get(url + '?' + urllib.parse.urlencode(args))

        key = model.device_id.key
        starting_at = self.datetime_to_ical(fix_datetime_weekday(model.cohort.kickoff_date,
                                                                 DatetimeInteger.to_datetime(
                                                                     model.cohort_time_slot.timezone,
                                                                     model.cohort_time_slot.starting_at),
                                                                 next=True),
                                            utc=False)

        starting_at_utc = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at),
                                                utc=True)

        ending_at = fix_datetime_weekday(model.cohort.kickoff_date,
                                         DatetimeInteger.to_datetime(model.cohort_time_slot.timezone,
                                                                     model.cohort_time_slot.ending_at),
                                         next=True)

        ending_at = self.datetime_to_ical(ending_at, utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model.academy.name}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 One time slot with teacher
    """

    def test_ical_cohorts__with_one__with_teacher(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)}
        teacher_kwargs = {'role': 'TEACHER'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        base = self.generate_models(academy=True,
                                    device_id=True,
                                    cohort=True,
                                    device_id_kwargs=device_id_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        models = [
            self.generate_models(cohort_user=True,
                                 cohort_time_slot=True,
                                 cohort_time_slot_kwargs=cohort_time_slot_kwargs,
                                 models=base),
            self.generate_models(cohort_user=True, models=base, cohort_user_kwargs=teacher_kwargs),
        ]

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        model1 = models[0]
        model2 = models[1]
        key = model1.device_id.key

        starting_at = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                                 DatetimeInteger.to_datetime(
                                                                     model1.cohort_time_slot.timezone,
                                                                     model1.cohort_time_slot.starting_at),
                                                                 next=True),
                                            utc=False)

        starting_at_utc = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model1.cohort_time_slot.timezone, model1.cohort_time_slot.starting_at),
                                                utc=True)

        ending_at = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                               DatetimeInteger.to_datetime(
                                                                   model1.cohort_time_slot.timezone,
                                                                   model1.cohort_time_slot.ending_at),
                                                               next=True),
                                          utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model1.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc}',
            f'UID:breathecode_cohort_time_slot_{model1.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model1.academy.name}',
            self.line_limit(f'ORGANIZER;CN="{model2.user.first_name} '
                            f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Two time slot with teacher
    """

    def test_ical_cohort__with_two__with_teacher(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)}
        teacher_kwargs = {'role': 'TEACHER'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        base = self.generate_models(academy=True,
                                    device_id=True,
                                    cohort=True,
                                    device_id_kwargs=device_id_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        models = [
            self.generate_models(cohort_user=True,
                                 cohort_time_slot=True,
                                 cohort_time_slot_kwargs=cohort_time_slot_kwargs,
                                 models=base),
            self.generate_models(cohort_user=True, models=base, cohort_user_kwargs=teacher_kwargs),
        ]

        models.append(
            self.generate_models(user=models[0].user,
                                 cohort_user=models[0].cohort_user,
                                 cohort_time_slot=True,
                                 cohort_time_slot_kwargs=cohort_time_slot_kwargs,
                                 models=base))

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        model1 = models[0]  # student
        model2 = models[1]  # teacher
        model3 = models[2]  # student
        key = model1.device_id.key

        starting_at1 = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                                  DatetimeInteger.to_datetime(
                                                                      model1.cohort_time_slot.timezone,
                                                                      model1.cohort_time_slot.starting_at),
                                                                  next=True),
                                             utc=False)

        starting_at3 = self.datetime_to_ical(fix_datetime_weekday(model3.cohort.kickoff_date,
                                                                  DatetimeInteger.to_datetime(
                                                                      model3.cohort_time_slot.timezone,
                                                                      model3.cohort_time_slot.starting_at),
                                                                  next=True),
                                             utc=False)

        starting_at_utc1 = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model1.cohort_time_slot.timezone, model1.cohort_time_slot.starting_at),
                                                 utc=True)

        starting_at_utc3 = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model3.cohort_time_slot.timezone, model3.cohort_time_slot.starting_at),
                                                 utc=True)

        ending_at1 = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                                DatetimeInteger.to_datetime(
                                                                    model1.cohort_time_slot.timezone,
                                                                    model1.cohort_time_slot.ending_at),
                                                                next=True),
                                           utc=False)

        ending_at3 = self.datetime_to_ical(fix_datetime_weekday(model3.cohort.kickoff_date,
                                                                DatetimeInteger.to_datetime(
                                                                    model3.cohort_time_slot.timezone,
                                                                    model3.cohort_time_slot.ending_at),
                                                                next=True),
                                           utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model1.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at1}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at1}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc1}',
            f'UID:breathecode_cohort_time_slot_{model1.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model1.academy.name}',
            self.line_limit(f'ORGANIZER;CN="{model2.user.first_name} '
                            f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'),
            'END:VEVENT',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model3.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at3}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at3}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc3}',
            f'UID:breathecode_cohort_time_slot_{model3.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model3.academy.name}',
            self.line_limit(f'ORGANIZER;CN="{model2.user.first_name} '
                            f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Two time slot with teacher
    """

    def test_ical_cohort__with_two__with_teacher__cohort_with_meeting_url(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'ending_date': datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0),
            'online_meeting_url': self.bc.fake.url(),
        }
        teacher_kwargs = {'role': 'TEACHER'}

        # don't forget 🦾 2021 - 1010
        datetime_interger = 202109111330
        cohort_time_slot_kwargs = {
            'timezone': 'America/Bogota',
            'starting_at': datetime_interger,
            'ending_at': datetime_interger,
        }

        base = self.generate_models(academy=True,
                                    device_id=True,
                                    cohort=True,
                                    device_id_kwargs=device_id_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        models = [
            self.generate_models(cohort_user=True,
                                 cohort_time_slot=True,
                                 cohort_time_slot_kwargs=cohort_time_slot_kwargs,
                                 models=base),
            self.generate_models(cohort_user=True, models=base, cohort_user_kwargs=teacher_kwargs),
        ]

        models.append(
            self.generate_models(user=models[0].user,
                                 cohort_user=models[0].cohort_user,
                                 cohort_time_slot=True,
                                 cohort_time_slot_kwargs=cohort_time_slot_kwargs,
                                 models=base))

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        model1 = models[0]  # student
        model2 = models[1]  # teacher
        model3 = models[2]  # student
        key = model1.device_id.key

        starting_at1 = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                                  DatetimeInteger.to_datetime(
                                                                      model1.cohort_time_slot.timezone,
                                                                      model1.cohort_time_slot.starting_at),
                                                                  next=True),
                                             utc=False)

        starting_at3 = self.datetime_to_ical(fix_datetime_weekday(model3.cohort.kickoff_date,
                                                                  DatetimeInteger.to_datetime(
                                                                      model3.cohort_time_slot.timezone,
                                                                      model3.cohort_time_slot.starting_at),
                                                                  next=True),
                                             utc=False)

        starting_at_utc1 = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model1.cohort_time_slot.timezone, model1.cohort_time_slot.starting_at),
                                                 utc=True)

        starting_at_utc3 = self.datetime_to_ical(DatetimeInteger.to_utc_datetime(
            model3.cohort_time_slot.timezone, model3.cohort_time_slot.starting_at),
                                                 utc=True)

        ending_at1 = self.datetime_to_ical(fix_datetime_weekday(model1.cohort.kickoff_date,
                                                                DatetimeInteger.to_datetime(
                                                                    model1.cohort_time_slot.timezone,
                                                                    model1.cohort_time_slot.ending_at),
                                                                next=True),
                                           utc=False)

        ending_at3 = self.datetime_to_ical(fix_datetime_weekday(model3.cohort.kickoff_date,
                                                                DatetimeInteger.to_datetime(
                                                                    model3.cohort_time_slot.timezone,
                                                                    model3.cohort_time_slot.ending_at),
                                                                next=True),
                                           utc=False)

        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'METHOD:PUBLISH',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model1.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at1}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at1}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc1}',
            f'UID:breathecode_cohort_time_slot_{model1.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model1.cohort.online_meeting_url}',
            self.line_limit(f'ORGANIZER;CN="{model2.user.first_name} '
                            f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'),
            'END:VEVENT',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model3.cohort.name}',
            f'DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:{starting_at3}',
            f'DTEND;TZID=America/Bogota;VALUE=DATE-TIME:{ending_at3}',
            f'DTSTAMP;VALUE=DATE-TIME:{starting_at_utc3}',
            f'UID:breathecode_cohort_time_slot_{model3.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T212600Z',
            f'LOCATION:{model3.cohort.online_meeting_url}',
            self.line_limit(f'ORGANIZER;CN="{model2.user.first_name} '
                            f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
