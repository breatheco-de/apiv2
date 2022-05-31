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
import random

TOTAL = 15

DATASTORE_SEED = [{
    'academy_id': 0,
    'cohort': None,
    'created_at': (timezone.now() + timedelta(days=1)).isoformat() + 'Z',
    'data': None,
    'day': 13,
    'email': 'konan@naruto.io',
    'slug': 'breathecode_login',
    'user_agent': 'bc/test',
    'user_id': 1,
}]


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
    🔽🔽🔽 Auth
    """
    def test_type__without_auth(self):
        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?slug=breathecode_login'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?slug=breathecode_login'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?slug=breathecode_login'
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': ("You (user: 1) don't have this capability: classroom_activity for "
                           'academy 1'),
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Without pagination
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=generate_data(3)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(TOTAL))
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

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = [DATASTORE_SEED[0], DATASTORE_SEED[0], DATASTORE_SEED[0]]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(
                kind='student_activity',
                cohort='miami-downtown-pt-xx',
            ),
        ])
        self.assertEqual(mock.count.call_args_list, [])

    """
    🔽🔽🔽 With limit
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=generate_data(10)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(TOTAL))
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

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?limit=5'
        response = self.client.get(url)

        json = response.json()
        data = {
            'academy_id': 0,
            'cohort': None,
            'data': None,
            'day': 13,
            'email': 'konan@naruto.io',
            'slug': 'breathecode_login',
            'user_agent': 'bc/test',
            'user_id': 1
        }

        wrapper = {
            'count': TOTAL,
            'first': None,
            'next': 'http://testserver/v1/activity/academy/cohort/1?limit=5&offset=5',
            'previous': None,
            'last': 'http://testserver/v1/activity/academy/cohort/1?limit=5&offset=10',
            'results': [data for _ in range(0, 5)]
        }

        for r in json['results']:
            self.assertDatetime(r['created_at'])
            del r['created_at']

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json, wrapper)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity', cohort='miami-downtown-pt-xx', limit=5),
        ])
        self.assertEqual(mock.count.call_args_list,
                         [call(
                             kind='student_activity',
                             cohort='miami-downtown-pt-xx',
                         )])

    """
    🔽🔽🔽 With limit and offset
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=generate_data(10)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(TOTAL))
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

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?offset=5&limit=5'
        response = self.client.get(url)
        json = response.json()
        data = {
            'academy_id': 0,
            'cohort': None,
            'data': None,
            'day': 13,
            'email': 'konan@naruto.io',
            'slug': 'breathecode_login',
            'user_agent': 'bc/test',
            'user_id': 1
        }

        wrapper = {
            'count': TOTAL,
            'first': 'http://testserver/v1/activity/academy/cohort/1?limit=5',
            'next': 'http://testserver/v1/activity/academy/cohort/1?limit=5&offset=10',
            'previous': 'http://testserver/v1/activity/academy/cohort/1?limit=5',
            'last': 'http://testserver/v1/activity/academy/cohort/1?limit=5&offset=10',
            'results': [data for _ in range(0, 5)]
        }

        for r in json['results']:
            self.assertDatetime(r['created_at'])
            del r['created_at']

        self.assertEqual(json, wrapper)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity', cohort='miami-downtown-pt-xx', limit=5, offset=5),
        ])
        self.assertEqual(mock.count.call_args_list,
                         [call(
                             kind='student_activity',
                             cohort='miami-downtown-pt-xx',
                         )])

    """
    🔽🔽🔽 With offset above the total items
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=generate_data(15)))
    @patch.object(Datastore, 'count', new=datastore_count_mock(TOTAL))
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

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?offset=10&limit=5'
        response = self.client.get(url)

        json = response.json()

        wrapper = {
            'count': TOTAL,
            'first': 'http://testserver/v1/activity/academy/cohort/1?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/activity/academy/cohort/1?limit=5&offset=5',
            'last': None,
            'results': [DATASTORE_SEED[0] for _ in range(0, 5)]
        }

        self.assertEqual(json, wrapper)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock.fetch.call_args_list, [
            call(kind='student_activity', cohort='miami-downtown-pt-xx', limit=5, offset=10),
        ])
        self.assertEqual(mock.count.call_args_list,
                         [call(
                             kind='student_activity',
                             cohort='miami-downtown-pt-xx',
                         )])

    """
    🔽🔽🔽 Without cohort
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
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

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?slug=breathecode_login'
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
            call(kind='student_activity', cohort='miami-downtown-pt-xx', slug='breathecode_login'),
        ])

    """
    🔽🔽🔽 Without valid cohort
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
    def test_get_activities_without_valid_cohort(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 'potato300'
                                                                 }) + '?slug=breathecode_login'
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json, {'detail': 'cohort-not-found', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Without valid slug activity
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
    def test_get_activities_without_valid_activity(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.fetch.call_args_list = []

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'miami-downtown-pt-xx'}
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='classroom_activity',
                             role='potato',
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('activity:academy_cohort_id', kwargs={'cohort_id': 1}) + '?slug=logout'
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json, {'detail': 'activity-not-found', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Invalid user_id
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
    def test_get_activities_invalid_user_id(self):
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
                           kwargs={'cohort_id': 1}) + '?slug=breathecode_login' + '&user_id=batman'
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json, {'detail': 'bad-user-id', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 User no exist
    """

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=DATASTORE_SEED))
    def test_get_activities_user_no_exists(self):
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
                           kwargs={'cohort_id': 1}) + '?slug=breathecode_login' + '&user_id=300'
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json, {'detail': 'user-not-exists', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
