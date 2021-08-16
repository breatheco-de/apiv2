"""
Test /answer
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import MediaTestCase

DATASTORE_SEED = []


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


def datastore_fetch_mock(first_fetch=[]):
    def fetch(**kwargs):

        return first_fetch

    return MagicMock(side_effect=fetch)


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 With data
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(1)))
    def test_get_activities(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:academy_cohort_id',
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


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 Without pagination
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(99)))
    def test_get_activities_without_pagination(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)

        json = response.json()

        self.assertEqual(len(json), 100)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(
                kind='student_activity',
                cohort='miami-downtown-pt-xx',
            ),
        ])


class MediaTestSuite(MediaTestCase):
    """
    🔽🔽🔽 With limit
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(10)))
    def test_get_activities_with_limit(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:academy_cohort_id',
                           kwargs={'cohort_id': 1}) + '?limit=10'
        response = self.client.get(url)

        json = response.json()
        count = json['count']

        self.assertEqual(count, 10)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity',
                 cohort='miami-downtown-pt-xx',
                 limit=10),
        ])
