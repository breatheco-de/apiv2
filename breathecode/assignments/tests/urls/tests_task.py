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
    def test_task__without_auth(self):
        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without ProfileAcademy
    """

    def test_task__without_profile_academy(self):
        model = self.bc.database.create(user=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'without-profile-academy',
            'status_code': 400,
        }

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without Task
    """

    def test_task__without_data(self):
        model = self.bc.database.create(user=True, profile_academy=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get with Task
    """

    def test_task__one_task__cohort_null(self):
        model = self.bc.database.create(profile_academy=True, task=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Get with two Task
    """

    def test_task__two_tasks(self):
        model = self.bc.database.create(profile_academy=True, task=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query academy
    """

    def test_task__query_academy__found_zero__academy_not_exists(self):
        model = self.bc.database.create(profile_academy=True, task=True, cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_one(self):
        model = self.bc.database.create(profile_academy=True, task=True, cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?academy={model.academy.slug}'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_one__cohort_null(self):
        model = self.bc.database.create(profile_academy=True, task=True, skip_cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_two(self):
        model = self.bc.database.create(profile_academy=True, task=2, cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?academy={model.academy.slug}'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_academy__found_two__cohort_null(self):
        model = self.bc.database.create(profile_academy=True, task=2, skip_cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query user
    """

    def test_task__query_user__found_zero__user_not_exists(self):
        model = self.bc.database.create(profile_academy=True, task=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=2'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_user__found_one(self):
        model = self.bc.database.create(profile_academy=True, task=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=1'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_user__found_two(self):
        model = self.bc.database.create(profile_academy=True, task=2, cohort=True)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=1'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_user__found_two__related_to_two_users(self):
        tasks = [{'user_id': 1}, {'user_id': 2}]
        model = self.bc.database.create(profile_academy=True, user=2, task=tasks, cohort=True)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=1'
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

        self.assertEquals(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
