"""
Test /final_project/<int:project_id>
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import AssignmentsTestCase


def get_serializer(self, task, user):
    return {
        'associated_slug': task.associated_slug,
        'created_at': self.bc.datetime.to_iso_string(task.created_at),
        'github_url': task.github_url,
        'id': task.id,
        'live_url': task.live_url,
        'revision_status': task.revision_status,
        'task_status': task.task_status,
        'task_type': task.task_type,
        'title': task.title,
        'description': task.description,
        'user': {
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name
        }
    }


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
