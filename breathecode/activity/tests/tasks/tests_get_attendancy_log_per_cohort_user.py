"""
Test /answer
"""
import logging
from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone

from breathecode.activity.tasks import get_attendancy_log_per_cohort_user
from breathecode.activity import tasks
from breathecode.utils import NDB

from ...models import Activity
from ..mixins import MediaTestCase

UTC_NOW = timezone.now()


def get_datastore_seed(slug, day, data={}):
    return {
        'academy_id': 1,
        'cohort': slug,
        'created_at': (timezone.now() + timedelta(days=1)).isoformat() + 'Z',
        'data': {
            'cohort': slug,
            'day': str(day),
        },
        'day': day,
        'email': 'konan@naruto.io',
        'slug': 'breathecode_login',
        'user_agent': 'bc/test',
        'user_id': 1,
        **data,
    }


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 Cohort not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test_not_found(self):
        get_attendancy_log_per_cohort_user.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Executing get_attendancy_log_per_cohort_user')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Cohort user not found')])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 With Cohort and CohortUser
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test_with_cohort_user(self):
        cohort = {'history_log': random.choice(['', None, {}, []])}
        model = self.bc.database.create(cohort=cohort, cohort_user=1)

        logging.Logger.info.call_args_list = []

        get_attendancy_log_per_cohort_user.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            self.bc.format.to_dict(model.cohort_user),
        ])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Executing get_attendancy_log_per_cohort_user'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(f'Cohort {model.cohort.slug} has no log yet'),
        ])

    """
    🔽🔽🔽 With Cohort and CohortUser
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test_with_cohort_user__user_do_not_assist(self):
        utc_now = timezone.now()
        day1 = str(random.randint(1, 9))
        day2 = str(random.randint(1, 9))
        current_module1 = random.randint(1, 9)
        current_module2 = random.randint(1, 9)
        cohort = {
            'history_log': {
                day1: {
                    'attendance_ids': [5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module1,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
                day2: {
                    'attendance_ids': [5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module2,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
            },
        }
        model = self.bc.database.create(cohort=cohort, cohort_user=1)

        logging.Logger.info.call_args_list = []

        get_attendancy_log_per_cohort_user.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            **self.bc.format.to_dict(model.cohort_user),
            'history_log': {
                'attendance': {},
                'unattendance': {
                    day1: {
                        'current_module': current_module1,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                    day2: {
                        'current_module': current_module2,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                },
            },
        }])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Executing get_attendancy_log_per_cohort_user'),
                          call('History log saved')])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 With Cohort and CohortUser
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test_with_cohort_user__user_assist(self):
        utc_now = timezone.now()
        day1 = str(random.randint(1, 9))
        day2 = str(random.randint(1, 9))
        current_module1 = random.randint(1, 9)
        current_module2 = random.randint(1, 9)
        cohort = {
            'history_log': {
                day1: {
                    'attendance_ids': [1, 5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module1,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
                day2: {
                    'attendance_ids': [1, 5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module2,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
            }
        }
        model = self.bc.database.create(cohort=cohort, cohort_user=1)

        logging.Logger.info.call_args_list = []

        get_attendancy_log_per_cohort_user.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'attendance': {
                        day1: {
                            'current_module': current_module1,
                            'updated_at': self.bc.datetime.to_iso_string(utc_now),
                        },
                        day2: {
                            'current_module': current_module2,
                            'updated_at': self.bc.datetime.to_iso_string(utc_now),
                        },
                    },
                    'unattendance': {},
                },
            },
        ])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Executing get_attendancy_log_per_cohort_user'),
                          call('History log saved')])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 With Cohort and CohortUser with bad history log
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test_with_cohort_user__with_bad_user_log(self):
        utc_now = timezone.now()
        available_days = {str(random.randint(1, 9)) for _ in range(4)}

        while len(available_days) < 4:
            available_days.add(str(random.randint(1, 9)))

        available_days = list(available_days)

        day1 = available_days[0]
        day2 = available_days[1]
        day3 = available_days[2]
        day4 = available_days[3]
        current_module1 = random.randint(1, 9)
        current_module2 = random.randint(1, 9)
        current_module3 = random.randint(1, 9)
        current_module4 = random.randint(1, 9)
        cohort = {
            'history_log': {
                day1: {
                    'attendance_ids': [1, 5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module1,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
                day2: {
                    'attendance_ids': [5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module2,
                    'teacher_comments': '',
                    'unattendance_ids': [1, 5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
                day3: {
                    'attendance_ids': [1, 5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module3,
                    'teacher_comments': '',
                    'unattendance_ids': [5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
                day4: {
                    'attendance_ids': [5453, 5417, 5448, 5337, 5424, 5351, 5358],
                    'current_module': current_module4,
                    'teacher_comments': '',
                    'unattendance_ids': [1, 5435],
                    'updated_at': self.bc.datetime.to_iso_string(utc_now),
                },
            },
        }

        cohort_user = {
            'history_log': {
                'attendance': {
                    day2: {
                        'current_module': current_module1,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                    day4: {
                        'current_module': current_module2,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                },
                'unattendance': {
                    day1: {
                        'current_module': current_module1,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                    day3: {
                        'current_module': current_module2,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                },
            },
        }
        model = self.bc.database.create(cohort=cohort, cohort_user=cohort_user)

        logging.Logger.info.call_args_list = []

        get_attendancy_log_per_cohort_user.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            **self.bc.format.to_dict(model.cohort_user),
            'history_log': {
                'attendance': {
                    day1: {
                        'current_module': current_module1,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                    day3: {
                        'current_module': current_module3,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                },
                'unattendance': {
                    day2: {
                        'current_module': current_module2,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                    day4: {
                        'current_module': current_module4,
                        'updated_at': self.bc.datetime.to_iso_string(utc_now),
                    },
                },
            },
        }])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Executing get_attendancy_log_per_cohort_user'),
                          call('History log saved')])
        self.assertEqual(logging.Logger.error.call_args_list, [])
