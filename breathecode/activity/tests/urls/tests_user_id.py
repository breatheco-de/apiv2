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
        'slug': 'breathecode-login',
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
    def test_user_id__without_auth(self):
        url = reverse_lazy('activity:user')
        data = {}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_id__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:user')
        data = {}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_id__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('activity:user')
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
    def test_user_id__post__missing_slug(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {}
        response = self.client.post(url, data)

        json = response.json()
        expected = {'detail': 'missing-slug', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__missing_user_agent(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
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
    def test_user_id__post__with_bad_slug(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'slug': 'they-killed-kenny',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'activity-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    """
    🔽🔽🔽 With public slug
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_public_slug(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'slug': 'breathecode-login',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')

        json = response.json()

        self.assertDatetime(json['created_at'])
        created_at = json['created_at']
        del json['created_at']

        expected = {
            'academy_id': 0,
            'email': model.user.email,
            'slug': 'breathecode-login',
            'user_agent': 'bc/test',
            'user_id': 1,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock.update.call_args_list, [
            call(
                'student_activity',
                {
                    'slug': 'breathecode-login',
                    'user_agent': 'bc/test',
                    'created_at': self.iso_to_datetime(created_at),
                    'user_id': 1,
                    'email': model.user.email,
                    'academy_id': 0,
                },
            ),
        ])

    """
    🔽🔽🔽 With private slug
    """
    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__missing_cohort(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'missing-cohort', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_private_slug__slug_require_a_cohort(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'cohort': 'they-killed-kenny',
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'missing-data', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_private_slug__slug_require_a_data(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'data': '',
            'cohort': 'they-killed-kenny',
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'data-is-not-a-json', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_private_slug__cohort_not_exist(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato')

        url = reverse_lazy('activity:user')
        data = {
            'data': '{"name": "Freyja"}',
            'cohort': 'they-killed-kenny',
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'cohort-not-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_private_slug__field_not_allowed(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato', cohort=True)

        url = reverse_lazy('activity:user')
        data = {
            'data': '{"name": "Freyja"}',
            'cohort': model.cohort.slug,
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
            'id': 1,
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'id-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock.update.call_args_list, [])

    @patch.object(Datastore, '__init__', new=lambda x: None)
    @patch.object(Datastore, 'update', new=datastore_mock())
    def test_user_id__post__with_private_slug__cohort_not_exist___(self):
        from breathecode.services.google_cloud import Datastore as mock
        mock.update.call_args_list = []

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True,
            capability='crud_activity', role='potato', cohort=True)

        url = reverse_lazy('activity:user')
        data = {
            'data': '{"name": "Freyja"}',
            'cohort': model.cohort.slug,
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'academy_id': 1,
            'cohort': model.cohort.slug,
            'data': '{"name": "Freyja"}',
            'email': model.user.email,
            'slug': 'nps-survey-answered',
            'user_agent': 'bc/test',
            'user_id': 1,
        }

        self.assertDatetime(json['created_at'])
        created_at = json['created_at']
        del json['created_at']

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock.update.call_args_list, [
            call(
                'student_activity',
                {
                    'cohort': model.cohort.slug,
                    'data': '{"name": "Freyja"}',
                    'user_agent': 'bc/test',
                    'created_at': self.iso_to_datetime(created_at),
                    'slug': 'nps-survey-answered',
                    'user_id': 1,
                    'email': model.user.email,
                    'academy_id': 1,
                },
            ),
        ])
