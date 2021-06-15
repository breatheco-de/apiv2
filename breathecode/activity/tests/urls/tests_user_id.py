"""
Test /answer
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import MediaTestCase

DATASTORE_SHARED_SEED = [
    {
        'academy_id': 0,
        'cohort': None,
        'created_at': (datetime.now() + timedelta(days=1)).isoformat() + 'Z',
        'data': None,
        'day': 13,
        'email': 'konan@naruto.io',
        'slug': 'breathecode_login',
        'user_agent': 'bc/test',
        'user_id': 1,
    },
]
DATASTORE_PRIVATE_SEED = [
    {
        'academy_id': 1,
        'cohort': 'miami-downtown-pt-xx',
        'created_at': (datetime.now() + timedelta(days=2)).isoformat() + 'Z',
        'data': '{"cohort": "miami-downtown-pt-xx", "day": "13"}',
        'day': 13,
        'email': 'konan@naruto.io',
        'slug': 'classroom_attendance',
        'user_agent': 'bc/test',
        'user_id': 1,
    },
]


def datastore_mock():
    def update(key: str, data: dict):
        pass

    return MagicMock(side_effect=update)


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Auth
    """
    def test_type__without_auth(self):
        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        data = {}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        data = {}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': (
                "You (user: 1) don't have this capability: crud_activity for "
                "academy 1"),
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Missing fields
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_type__post__missing_slug(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        data = {}
        response = self.client.post(url, data)

        json = response.json()
        expected = {'detail': 'missing-slug', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_type__post__missing_user_agent(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        data = {'slug': 'they-killed-kenny'}
        response = self.client.post(url, data)

        json = response.json()
        expected = {'detail': 'missing-user-agent', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 Bad slug
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_typee__post__a___(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user_id', kwargs={'user_id': 1})
        data = {
            'slug': 'breathecode_login',
            'user_agent': 'bc/test'
        }
        response = self.client.post(url, data, format='json')

        json = response.json()

        self.assertDatetime(json['created_at'])
        created_at = json['created_at']
        del json['created_at']

        expected = {
            'academy_id': 0,
            'email': model.user.email,
            'slug': 'breathecode_login',
            'user_agent': 'bc/test',
            'user_id': 1
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock.update.call_args_list, [
            call(
                'student_activity',
                {
                    'slug': 'breathecode_login',
                    'user_agent': 'bc/test',
                    'created_at': created_at,
                    'user_id': 1,
                    'email': 'trujillokristie@hotmail.com',
                    'academy_id': 0,
                }
            )
        ])
