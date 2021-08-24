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


# def datastore_fetch_mock(first_fetch=[]):
#     def fetch(**kwargs):
#         return first_fetch

#     return MagicMock(side_effect=fetch)


def datastore_fetch_mock(first_fetch=[]):
    class Vars():
        fetch_call_counter = 0
        fetch_call_one = first_fetch

    Vars.fetch_call_counter = 0

    def fetch(**kwargs):
        Vars.fetch_call_counter += 1

        if Vars.fetch_call_counter % 2 == 1:
            result = Vars.fetch_call_one
            offset = 0
            try:
                limit = kwargs['limit']
                offset = kwargs['offset']
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
    🔽🔽🔽 With data
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
    @patch.object(Datastore, 'count', new=datastore_count_mock(7957599))
    def test_get_activities_slug_filtered(self):
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

    """
    🔽🔽🔽 Without pagination
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(100)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(7957599))
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

    """
    🔽🔽🔽 With limit
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(10)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(7957599))
    def test_get_activities_limit(self):
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
        results = len(json['results'])

        self.assertEqual(results, 10)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity',
                 cohort='miami-downtown-pt-xx',
                 limit=10),
        ])

    """
    🔽🔽🔽 With limit and offset
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(10)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(7957599))
    def test_get_activities_offset(self):
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
                           kwargs={'cohort_id': 1}) + '?offset=5&limit=5'
        response = self.client.get(url)

        json = response.json()
        results = len(json['results'])

        self.assertEqual(results, 5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity',
                 cohort='miami-downtown-pt-xx',
                 limit=5,
                 offset=5),
        ])

    """
    🔽🔽🔽 With offset above the total items
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore,
                  'fetch',
                  new=datastore_fetch_mock(first_fetch=generate_data(20)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(7957599))
    def test_get_activities_with_limit_and_offset(self):
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
                           kwargs={'cohort_id': 1}) + '?offset=20&limit=10'
        response = self.client.get(url)

        json = response.json()
        results = len(json['results'])

        self.assertEqual(results, 0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity',
                 cohort='miami-downtown-pt-xx',
                 limit=10,
                 offset=20),
        ])
