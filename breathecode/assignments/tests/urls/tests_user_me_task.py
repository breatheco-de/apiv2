"""
Test /answer
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import AssignmentsTestCase


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Auth
    """
    def test_user_me_task__without_auth(self):
        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without Task
    """

    def test_user_me_task__without_task(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get with one Task
    """

    def test_user_me_task__with_one_task(self):
        model = self.bc.database.create(user=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = [{
            'associated_slug': model.task.associated_slug,
            'github_url': model.task.github_url,
            'id': model.task.id,
            'live_url': model.task.live_url,
            'revision_status': model.task.revision_status,
            'task_status': model.task.task_status,
            'task_type': model.task.task_type,
            'title': model.task.title,
            'user': {
                'first_name': model.user.first_name,
                'id': model.user.id,
                'last_name': model.user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Get with two Task
    """

    def test_user_me_task__with_two_task(self):
        model = self.bc.database.create(user=1, task=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = [{
            'associated_slug': task.associated_slug,
            'github_url': task.github_url,
            'id': task.id,
            'live_url': task.live_url,
            'revision_status': task.revision_status,
            'task_status': task.task_status,
            'task_type': task.task_type,
            'title': task.title,
            'user': {
                'first_name': model.user.first_name,
                'id': model.user.id,
                'last_name': model.user.last_name
            }
        } for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Get with one Task but the other user
    """

    def test_user_me_task__with_one_task__but_the_other_user(self):
        task = {'user_id': 2}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Get with two Task but the other user
    """

    def test_user_me_task__with_two_tasks__but_the_other_user(self):
        task = {'user_id': 2}
        model = self.bc.database.create(user=2, task=(2, task))
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
