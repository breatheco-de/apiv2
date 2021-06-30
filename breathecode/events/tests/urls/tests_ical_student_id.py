"""
Test /academy/cohort
"""
from datetime import datetime, timedelta
import urllib
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_events_tests_case import EventTestCase


class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""
    """
    🔽🔽🔽 Without student
    """
    def test_ical_cohorts__without_student(self):
        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'academy': "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))
        json = response.json()

        expected = {
            "detail": 'student-not-exist',
            "status_code": 404,
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
    🔽🔽🔽 One time slot
    """

    def test_ical_cohorts__with_one(self):
        device_id_kwargs = {'name': 'server'}
        cohort_kwargs = {
            'ending_date':
            datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)
        }
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T120000Z',
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
        cohort_kwargs = {
            'ending_date':
            datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)
        }
        cohort_time_slot_kwargs = {'recurrent': False}
        model = self.generate_models(
            academy=True,
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
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
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
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=21001231T120000Z',
            f'LOCATION:{model.academy.name}',
            'END:VEVENT',
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
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
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

    def test_ical_cohorts__with_one__with_incoming_true__return_zero_time_slots(
            self):
        device_id_kwargs = {'name': 'server'}
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'upcoming': "true"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
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
        cohort_kwargs = {'kickoff_date': datetime.now() + timedelta(days=2)}
        model = self.generate_models(academy=True,
                                     device_id=True,
                                     device_id_kwargs=device_id_kwargs,
                                     cohort_user=True,
                                     cohort_time_slot=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        args = {'upcoming': "true"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=21001231T120000Z',
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
        cohort_kwargs = {
            'ending_date':
            datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)
        }
        teacher_kwargs = {'role': 'TEACHER'}
        base = self.generate_models(academy=True,
                                    device_id=True,
                                    cohort=True,
                                    device_id_kwargs=device_id_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        models = [
            self.generate_models(cohort_user=True,
                                 cohort_time_slot=True,
                                 models=base),
            self.generate_models(cohort_user=True,
                                 models=base,
                                 cohort_user_kwargs=teacher_kwargs),
        ]

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        model1 = models[0]
        model2 = models[1]
        key = model1.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model1.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model1.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T120000Z',
            f'LOCATION:{model1.academy.name}',
            self.line_limit(
                f'ORGANIZER;CN="{model2.user.first_name} '
                f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'
            ),
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
        cohort_kwargs = {
            'ending_date':
            datetime(year=2060, day=31, month=12, hour=12, minute=0, second=0)
        }
        teacher_kwargs = {'role': 'TEACHER'}
        base = self.generate_models(academy=True,
                                    device_id=True,
                                    cohort=True,
                                    device_id_kwargs=device_id_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        models = [
            self.generate_models(cohort_user=True,
                                 cohort_time_slot=True,
                                 models=base),
            self.generate_models(cohort_user=True,
                                 models=base,
                                 cohort_user_kwargs=teacher_kwargs),
        ]

        models.append(
            self.generate_models(user=models[0].user,
                                 cohort_user=models[0].cohort_user,
                                 cohort_time_slot=True,
                                 models=base))

        url = reverse_lazy('events:ical_student_id', kwargs={'user_id': 1})
        response = self.client.get(url)

        model1 = models[0]  # student
        model2 = models[1]  # teacher
        model3 = models[2]  # student
        key = model1.device_id.key
        expected = '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            f'PRODID:-//BreatheCode//Student Schedule (1) {key}//EN',
            'REFRESH-INTERVAL;VALUE=DURATION:PT15M',
            'URL:http://localhost:8000/v1/events/ical/student/1',
            'X-WR-CALDESC:',
            'X-WR-CALNAME:Academy - Schedule',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model1.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model1.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model1.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T120000Z',
            f'LOCATION:{model1.academy.name}',
            self.line_limit(
                f'ORGANIZER;CN="{model2.user.first_name} '
                f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'
            ),
            'END:VEVENT',
            # event
            'BEGIN:VEVENT',
            f'SUMMARY:{model3.cohort.name}',
            f'DTSTART;VALUE=DATE-TIME:{self.datetime_to_ical(model3.cohort_time_slot.starting_at)}',
            f'DTEND;VALUE=DATE-TIME:{self.datetime_to_ical(model3.cohort_time_slot.ending_at)}',
            f'DTSTAMP;VALUE=DATE-TIME:{self.datetime_to_ical(model3.cohort_time_slot.starting_at)}',
            f'UID:breathecode_cohort_time_slot_{model3.cohort_time_slot.id}_{key}',
            f'RRULE:FREQ=WEEKLY;UNTIL=20601231T120000Z',
            f'LOCATION:{model3.academy.name}',
            self.line_limit(
                f'ORGANIZER;CN="{model2.user.first_name} '
                f'{model2.user.last_name}";ROLE=OWNER:MAILTO:{model2.user.email}'
            ),
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
