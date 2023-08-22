"""
Test /answer
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ...mixins import MediaTestCase


class MediaTestSuite(MediaTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Auth
    """

    def test_type__without_auth(self):
        url = reverse_lazy('v2:activity:me_activity')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('v2:activity:me_activity')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_type__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('v2:activity:me_activity')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': ("You (user: 1) don't have this capability: read_activity for "
                           'academy 1'),
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # """
    # 🔽🔽🔽 Without data
    # """

    # @patch.object(Datastore, '__init__', new=lambda x: None)
    # @patch.object(Datastore, 'fetch', new=datastore_fetch_mock(first_fetch=[], second_fetch=[]))
    # def test_type__without_data(self):
    #     from breathecode.services.google_cloud import Datastore as mock
    #     mock.fetch.call_args_list = []

    #     self.headers(academy=1)
    #     self.generate_models(authenticate=True,
    #                          profile_academy=True,
    #                          capability='read_activity',
    #                          role='potato')

    #     url = reverse_lazy('v2:activity:me_activity')
    #     response = self.client.get(url)

    #     json = response.json()
    #     expected = []

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(mock.fetch.call_args_list, [
    #         call(kind='student_activity', academy_id=1),
    #         call(kind='student_activity', academy_id=0),
    #     ])
