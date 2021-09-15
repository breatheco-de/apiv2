"""
Test /answer
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from google.cloud import ndb
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import MediaTestCase
import random

RANDOM_COUNT = random.randint(1, 1000)

DATASTORE_SEED = [{
    'academy_id':
    0,
    'cohort':
    None,
    'created_at': (timezone.now() + timedelta(days=1)).isoformat() + 'Z',
    'data':
    None,
    'day':
    13,
    'email':
    'konan@naruto.io',
    'slug':
    'breathecode_login',
    'user_agent':
    'bc/test',
    'user_id':
    1,
}]


def generate_data(num_objs):
    DATASTORE_SEED = []
    for x in range(num_objs):
        DATASTORE_SEED.append({
            'academy_id':
            0,
            'cohort':
            None,
            'created_at':
            (timezone.now() + timedelta(days=1)).isoformat() + 'Z',
            'data':
            None,
            'day':
            13,
            'email':
            'konan@naruto.io',
            'slug':
            'breathecode_login',
            'user_agent':
            'bc/test',
            'user_id':
            1,
        })
    return DATASTORE_SEED


class MockContext():
    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass


class QueryMock:
    def filter(self, *args, **kwargs):
        return MagicMock(side_effect=MockContext)


class QueryFetchMock:
    def fetch(self, *args, **kwargs):
        return MagicMock(side_effect=MockContext)


def datastore_context_mock():
    # class Model():
    def query(**kwargs):
        pass

    def filter(**kwargs):
        pass

    def fetch(**kwargs):
        return []

    return MagicMock(side_effect=MockContext)


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 With data
    """
    @patch.object(ndb.Client, '__init__', new=lambda x: None)
    @patch.object(ndb.Client, 'context', new=datastore_context_mock())
    def test_get_activities_slug_filtered(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        print('hello')

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:cohort_id',
                           kwargs={'cohort_id': 1}) + '?slug=breathecode_login'
        response = self.client.get(url)

        json = response.json()
        expected = [
            {
                'academy_id': 0,
                'cohort': None,
                'created_at': DATASTORE_SEED[0]['created_at'],
                'data': None,
                'day': 13,
                'email': 'konan@naruto.io',
                'slug': 'breathecode_login',
                'user_agent': 'bc/test',
                'user_id': 1,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity',
                 cohort='miami-downtown-pt-xx',
                 slug='breathecode_login'),
        ])
        self.assertEqual(mock.count.call_args_list, [])
