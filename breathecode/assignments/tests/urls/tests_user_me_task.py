"""
Test /answer
"""
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from pytz import UTC
from rest_framework import status
import random
from breathecode.services.google_cloud import Datastore

from ..mixins import AssignmentsTestCase

UTC_NOW = timezone.now()


def put_serializer(self, task, data={}):
    return {
        'associated_slug': task.associated_slug,
        'cohort': task.cohort,
        'created_at': self.bc.datetime.to_iso_string(task.created_at),
        'description': task.description,
        'github_url': task.github_url,
        'id': task.id,
        'live_url': task.live_url,
        'revision_status': task.revision_status,
        'task_status': task.task_status,
        'task_type': task.task_type,
        'title': task.title,
        'updated_at': self.bc.datetime.to_iso_string(task.updated_at),
        **data
    }


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
            'description': model.task.description,
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
            'description': task.description,
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

    """
    🔽🔽🔽 Delete
    """

    def test_delete_tasks_in_bulk_found_and_deleted(self):

        model = self.bc.database.create(user=1, task=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task') + '?id=1,2'
        print(url)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    def test_delete_tasks_in_bulk_tasks_not_found(self):

        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task') + '?id=1,2'
        response = self.client.delete(url)

        json = response.json()
        expected = {
            'failure': [{
                'detail':
                'task-not-found',
                'resources': [{
                    'display_field': 'pk',
                    'display_value': 1,
                    'pk': 1
                }, {
                    'display_field': 'pk',
                    'display_value': 2,
                    'pk': 2
                }],
                'status_code':
                404
            }],
            'success': []
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    def test_delete_task_in_bulk_associated_with_another_user(self):

        model = self.bc.database.create(user=2, task=2)
        self.bc.request.authenticate(model.user[1])

        url = reverse_lazy('assignments:user_me_task') + '?id=1,2'
        response = self.client.delete(url)

        json = response.json()
        expected = {
            'failure': [{
                'detail':
                'task-not-found-for-this-user',
                'resources': [{
                    'display_field': 'associated_slug',
                    'display_value': x.associated_slug,
                    'pk': x.pk
                } for x in model.task],
                'status_code':
                400
            }],
            'success': []
        }

        self.assertEqual(json, expected)

        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Put
    """

    def test_put__without_task(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'update-whout-list', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    def test_put_passing_empty_list(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [], format='json')

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    def test_put_passing_no_id(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [{}], format='json')

        json = response.json()
        expected = {'detail': 'missing=task-id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    def test_put_passing_wrong_id(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [{'id': 1}], format='json')

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_put_passing_taks_id(self):
        model = self.bc.database.create(user=1, task=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [{'id': 1}, {'id': 2}], format='json')

        json = response.json()

        expected = [
            put_serializer(self, x, {'updated_at': self.bc.datetime.to_iso_string(UTC_NOW)})
            for x in model.task
        ]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_put_passing_random_values_to_update_task(self):
        model = self.bc.database.create(user=1, task=2, cohort=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')

        data = [{
            'id': n,
            'title': self.bc.fake.name(),
            'task_status': random.choice(['PENDING', 'DONE']),
            'revision_status': 'PENDING',
            'github_url': self.bc.fake.url(),
            'live_url': self.bc.fake.url(),
            'description': self.bc.fake.text()[:450],
            'cohort': random.randint(1, 2)
        } for n in range(1, 3)]
        response = self.client.put(url, data, format='json')

        json = response.json()

        print(json)
        print(data)

        expected = [
            put_serializer(self, model.task[x], {
                'updated_at': self.bc.datetime.to_iso_string(UTC_NOW),
                **data[x]
            }) for x in range(0, 2)
        ]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
