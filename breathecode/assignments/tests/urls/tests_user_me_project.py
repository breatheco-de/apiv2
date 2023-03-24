"""
Test /final_project/<int:project_id>
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import AssignmentsTestCase


class FinalProjectTestSuite(AssignmentsTestCase):
    """Test /final_project"""
    """
    🔽🔽🔽 Auth
    """

    def test_final_project_with_no_auth(self):
        url = reverse_lazy('assignments:user_me_project', kwargs={'project_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_final_project_with_wrong_id(self):

        self.bc.request.set_headers(academy=1)
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
        )
        url = reverse_lazy('assignments:user_me_project', kwargs={'project_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'project-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_final_project_with_wrong_id(self):

        self.bc.request.set_headers(academy=1)
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
        )
        url = reverse_lazy('assignments:user_me_project', kwargs={'project_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'project-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_final_project_when_not_a_member(self):

        self.bc.request.set_headers(academy=1)
        user_models = self.bc.database.create(user=[{'id': 1}, {'id': 2}], )
        models = self.bc.database.create(authenticate=True, profile_academy=2, final_project={'members': [2]})
        url = reverse_lazy('assignments:user_me_project', kwargs={'project_id': 1})
        data = {'name': 'Facebook'}
        response = self.client.put(url, data)

        json = response.json()
        expected = {'detail': 'not-a-member', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
