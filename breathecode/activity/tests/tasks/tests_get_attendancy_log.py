"""
Test /answer
"""
import logging
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils import NDB

from breathecode.services.google_cloud import Datastore

from ...models import Activity
from ..mixins import MediaTestCase
from breathecode.activity.tasks import get_attendancy_log
import random

# get_attendancy_log
TOTAL = 15

DATASTORE_SEED = [{
    'academy_id': 1,
    'cohort': None,
    'created_at': (timezone.now() + timedelta(days=1)).isoformat() + 'Z',
    'data': {
        'cohort': 'santiago-pt-24',
        'day': '10',
    },
    'day': 13,
    'email': 'konan@naruto.io',
    'slug': 'classroom_attendance',
    'user_agent': 'bc/test',
    'user_id': 1,
}]


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


def generate_data(num_objs):
    datastore_seed = []
    for _ in range(num_objs):
        datastore_seed.append(DATASTORE_SEED[0])
    return datastore_seed


def datastore_fetch_mock(first_fetch=[]):

    class Vars():
        fetch_call_counter = 0
        fetch_call_one = first_fetch

    Vars.fetch_call_counter = 0

    def fetch(**kwargs):
        Vars.fetch_call_counter += 1

        if Vars.fetch_call_counter % 2 == 1:
            result = Vars.fetch_call_one
            offset = kwargs['offset'] if 'offset' in kwargs else 0
            try:
                limit = kwargs['limit']
                # offset = kwargs['offset']
            except:
                return result
            if limit is not None:
                return result[offset:offset + limit]
        return []

    return MagicMock(side_effect=fetch)


def datastore_count_mock(how_many):

    def count(**kwargs):
        return how_many

    return MagicMock(side_effect=count)


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 Cohort not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    @patch.object(NDB, 'fetch', MagicMock(return_value=DATASTORE_SEED))
    def test_not_found(self):
        get_attendancy_log.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [call('Executing get_attendancy_log')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Cohort not found')])

        self.assertEqual(NDB.__init__.call_args_list, [])
        self.assertEqual(NDB.fetch.call_args_list, [])

    """
    🔽🔽🔽 Syllabus not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    @patch.object(NDB, 'fetch', MagicMock(return_value=DATASTORE_SEED))
    def test_syllabus_not_found(self):
        model = self.bc.database.create(cohort=1)

        logging.Logger.info.call_args_list = []

        get_attendancy_log.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(logging.Logger.info.call_args_list, [call('Executing get_attendancy_log')])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(f'Cohort {model.cohort.slug} not have syllabus too'),
        ])

        self.assertEqual(NDB.__init__.call_args_list, [])
        self.assertEqual(NDB.fetch.call_args_list, [])

    """
    🔽🔽🔽 SyllabusVersion has json with bad format
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    @patch.object(NDB, 'fetch', MagicMock(return_value=DATASTORE_SEED))
    def test_syllabus_version_with_json_with_bad_format(self):
        syllabus_versions = [
            {
                'json': {}
            },
            {
                'json': []
            },
            {
                'json': {
                    'days': None
                }
            },
            {
                'json': {
                    'days': {}
                }
            },
            {
                'json': {
                    'days': [{}]
                }
            },
            {
                'json': {
                    'days': [{
                        'id': 1
                    }]
                }
            },
            {
                'json': {
                    'days': [{
                        'duration_in_days': 1
                    }]
                }
            },
            {
                'json': {
                    'days': [{
                        'label': 1
                    }]
                }
            },
        ]
        for syllabus_version in syllabus_versions:
            model = self.bc.database.create(cohort=1, syllabus_version=syllabus_version)

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            get_attendancy_log.delay(model.cohort.id)

            self.assertEqual(logging.Logger.info.call_args_list, [call('Executing get_attendancy_log')])
            self.assertEqual(logging.Logger.error.call_args_list, [
                call(f'Cohort {model.cohort.slug} have syllabus with bad format'),
            ])

            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
                self.bc.format.to_dict(model.cohort),
            ])

            self.assertEqual(self.bc.database.list_of('admissions.SyllabusVersion'), [
                self.bc.format.to_dict(model.syllabus_version),
            ])

            self.assertEqual(NDB.__init__.call_args_list, [])
            self.assertEqual(NDB.fetch.call_args_list, [])

            # teardown
            self.bc.database.delete('admissions.Cohort')
            self.bc.database.delete('admissions.SyllabusVersion')

    """
    🔽🔽🔽 The student attended the first day
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    def test_the_student_attended_the_first_day(self):
        cases = [
            ([get_datastore_seed(self.bc.fake.slug(), 1, {'slug': 'classroom_attendance'})], [], [1], []),
            ([], [get_datastore_seed(self.bc.fake.slug(), 1, {'slug': 'classroom_unattendance'})], [], [1]),
            ([get_datastore_seed(self.bc.fake.slug(), 1, {'slug': 'classroom_attendance'})],
             [get_datastore_seed(self.bc.fake.slug(), 1, {'slug': 'classroom_unattendance'})], [1], [1]),
        ]
        syllabus_version = {
            'json': {
                'days': [{
                    'id': x,
                    'duration_in_days': 1,
                    'label': self.bc.fake.slug(),
                } for x in range(1, 4)]
            }
        }

        model = self.bc.database.create(cohort=1, syllabus_version=syllabus_version)

        for attendance_seed, unattendance_seed, attendance_ids, unattendance_ids in cases:
            model.cohort.history_log = {}
            model.cohort.save()

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            with patch.object(NDB, 'fetch', MagicMock(side_effect=[attendance_seed, unattendance_seed])):
                get_attendancy_log.delay(model.cohort.id)

                self.assertEqual(NDB.__init__.call_args_list, [call(Activity)])
                self.assertEqual(NDB.fetch.call_args_list, [
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_attendance']),
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_unattendance']),
                ])

            self.assertEqual(logging.Logger.info.call_args_list, [
                call('Executing get_attendancy_log'),
                call('History log saved'),
            ])
            self.assertEqual(logging.Logger.error.call_args_list, [])

            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
                **self.bc.format.to_dict(model.cohort),
                'history_log': [{
                    'current_module': x['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                } for x in model.syllabus_version.json['days'][:1]] + [{
                    'current_module': x['label'],
                    'attendance_ids': None,
                    'unattendance_ids': None,
                } for x in model.syllabus_version.json['days'][1:]],
            }])

            self.assertEqual(self.bc.database.list_of('admissions.SyllabusVersion'), [{
                **self.bc.format.to_dict(model.syllabus_version),
            }])

            # teardown
            NDB.__init__.call_args_list = []

    """
    🔽🔽🔽 The students attended all days
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    def test_the_students_attended_all_days(self):
        cases = [
            ([
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 3,
                }),
            ], [], [1], []),
            ([], [
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 3,
                }),
            ], [], [1]),
            ([
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 3,
                }),
            ], [
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 3,
                }),
            ], [1], [1]),
        ]
        syllabus_version = {
            'json': {
                'days': [{
                    'id': x,
                    'duration_in_days': 1,
                    'label': self.bc.fake.slug(),
                } for x in range(1, 4)]
            }
        }

        model = self.bc.database.create(cohort=1, syllabus_version=syllabus_version)

        for attendance_seed, unattendance_seed, attendance_ids, unattendance_ids in cases:
            model.cohort.history_log = {}
            model.cohort.save()

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            with patch.object(NDB, 'fetch', MagicMock(side_effect=[attendance_seed, unattendance_seed])):
                get_attendancy_log.delay(model.cohort.id)

                self.assertEqual(NDB.__init__.call_args_list, [call(Activity)])
                self.assertEqual(NDB.fetch.call_args_list, [
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_attendance']),
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_unattendance']),
                ])

            self.assertEqual(logging.Logger.info.call_args_list, [
                call('Executing get_attendancy_log'),
                call('History log saved'),
            ])
            self.assertEqual(logging.Logger.error.call_args_list, [])

            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
                **self.bc.format.to_dict(model.cohort),
                'history_log': [{
                    'current_module': x['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                } for x in model.syllabus_version.json['days']],
            }])

            self.assertEqual(self.bc.database.list_of('admissions.SyllabusVersion'), [{
                **self.bc.format.to_dict(model.syllabus_version),
            }])

            # teardown
            NDB.__init__.call_args_list = []

    """
    🔽🔽🔽 The students attended all days
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(NDB, '__init__', MagicMock(return_value=None))
    def test_the_students_attended_all_days__(self):
        cases = [
            ([
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 3,
                }),
                get_datastore_seed(self.bc.fake.slug(), 4, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 4,
                }),
                get_datastore_seed(self.bc.fake.slug(), 5, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 5,
                }),
                get_datastore_seed(self.bc.fake.slug(), 6, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 6,
                }),
                get_datastore_seed(self.bc.fake.slug(), 7, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 7,
                }),
            ], [], [1], []),
            ([], [
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 3,
                }),
                get_datastore_seed(self.bc.fake.slug(), 4, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 4,
                }),
                get_datastore_seed(self.bc.fake.slug(), 5, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 5,
                }),
                get_datastore_seed(self.bc.fake.slug(), 6, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 6,
                }),
                get_datastore_seed(self.bc.fake.slug(), 7, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 7,
                }),
            ], [], [1]),
            ([
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 3,
                }),
                get_datastore_seed(self.bc.fake.slug(), 4, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 4,
                }),
                get_datastore_seed(self.bc.fake.slug(), 5, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 5,
                }),
                get_datastore_seed(self.bc.fake.slug(), 6, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 6,
                }),
                get_datastore_seed(self.bc.fake.slug(), 7, {
                    'slug': 'classroom_attendance',
                    'user_id': 1,
                    'day': 7,
                }),
            ], [
                get_datastore_seed(self.bc.fake.slug(), 1, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 1,
                }),
                get_datastore_seed(self.bc.fake.slug(), 2, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 2,
                }),
                get_datastore_seed(self.bc.fake.slug(), 3, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 3,
                }),
                get_datastore_seed(self.bc.fake.slug(), 4, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 4,
                }),
                get_datastore_seed(self.bc.fake.slug(), 5, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 5,
                }),
                get_datastore_seed(self.bc.fake.slug(), 6, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 6,
                }),
                get_datastore_seed(self.bc.fake.slug(), 7, {
                    'slug': 'classroom_unattendance',
                    'user_id': 1,
                    'day': 7,
                }),
            ], [1], [1]),
        ]
        syllabus_version = {
            'json': {
                'days': [{
                    'id': x,
                    'duration_in_days': x,
                    'label': self.bc.fake.slug(),
                } for x in range(1, 4)]
            }
        }

        model = self.bc.database.create(cohort=1, syllabus_version=syllabus_version)

        for attendance_seed, unattendance_seed, attendance_ids, unattendance_ids in cases:
            model.cohort.history_log = {}
            model.cohort.save()

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            with patch.object(NDB, 'fetch', MagicMock(side_effect=[attendance_seed, unattendance_seed])):
                get_attendancy_log.delay(model.cohort.id)

                self.assertEqual(NDB.__init__.call_args_list, [call(Activity)])
                self.assertEqual(NDB.fetch.call_args_list, [
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_attendance']),
                    call([Activity.cohort == model.cohort.slug, Activity.slug == 'classroom_unattendance']),
                ])

            self.assertEqual(logging.Logger.info.call_args_list, [
                call('Executing get_attendancy_log'),
                call('History log saved'),
            ])
            self.assertEqual(logging.Logger.error.call_args_list, [])

            day1 = model.syllabus_version.json['days'][0]
            day2 = model.syllabus_version.json['days'][1]
            day3 = model.syllabus_version.json['days'][2]
            history_log = [
                {
                    'current_module': day1['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
                {
                    'current_module': day2['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
                {
                    'current_module': day2['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
                {
                    'current_module': day3['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
                {
                    'current_module': day3['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
                {
                    'current_module': day3['label'],
                    'attendance_ids': attendance_ids,
                    'unattendance_ids': unattendance_ids,
                },
            ]
            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
                {
                    **self.bc.format.to_dict(model.cohort),
                    'history_log': history_log,
                },
            ])

            self.assertEqual(self.bc.database.list_of('admissions.SyllabusVersion'), [{
                **self.bc.format.to_dict(model.syllabus_version),
            }])

            # teardown
            NDB.__init__.call_args_list = []
