"""
Test /answer
"""
import random
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

import breathecode.activity.tasks as activity_tasks
from breathecode.assignments import tasks
from breathecode.assignments.caches import TaskCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from capyc.rest_framework import pytest as capy

from ..mixins import AssignmentsTestCase

UTC_NOW = timezone.now()


def db_item(data={}):
    return {
        'associated_slug': 'live-ball-onto-go',
        'cohort_id': 1,
        'delivered_at': None,
        'description': '',
        'github_url': None,
        'id': 1,
        'live_url': None,
        'opened_at': None,
        'revision_status': 'PENDING',
        'rigobot_repository_id': None,
        'subtasks': None,
        'task_status': 'PENDING',
        'task_type': 'EXERCISE',
        'telemetry_id': None,
        'title': 'Richard Stephens',
        'user_id': 1,
        **data
    }


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
        'opened_at': self.bc.datetime.to_iso_string(task.opened_at) if task.opened_at else task.opened_at,
        **data
    }


def get_serializer(self, task, user):
    return {
        'associated_slug': task.associated_slug,
        'created_at': self.bc.datetime.to_iso_string(task.created_at),
        'updated_at': self.bc.datetime.to_iso_string(task.updated_at),
        'github_url': task.github_url,
        'id': task.id,
        'live_url': task.live_url,
        'revision_status': task.revision_status,
        'task_status': task.task_status,
        'task_type': task.task_type,
        'title': task.title,
        'assignment_telemetry': task.telemetry.telemetry if task.telemetry else None,
        'description': task.description,
        'opened_at': self.bc.datetime.to_iso_string(task.opened_at) if task.opened_at else task.opened_at,
        'delivered_at': self.bc.datetime.to_iso_string(task.delivered_at) if task.delivered_at else task.delivered_at,
        'user': {
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name
        }
    }


def post_serializer(data={}):
    return {
        'associated_slug': 'growth-purpose',
        'attachments': [],
        'cohort': 1,
        'created_at': '2024-04-25T01:09:44.447234Z',
        'delivered_at': None,
        'description': '',
        'github_url': None,
        'id': 1,
        'live_url': None,
        'opened_at': None,
        'revision_status': 'PENDING',
        'rigobot_repository_id': None,
        'subtasks': None,
        'task_status': 'PENDING',
        'task_type': 'EXERCISE',
        'telemetry': None,
        'title': 'Isabella Duffy',
        'updated_at': '2024-04-25T01:09:44.447254Z',
        **data,
    }


def put_serializer(self, task, data={}):
    return {
        'associated_slug': task.associated_slug,
        'cohort': task.cohort.id if task.cohort else None,
        'created_at': self.bc.datetime.to_iso_string(task.created_at),
        'description': task.description,
        'github_url': task.github_url,
        'id': task.id,
        'live_url': task.live_url,
        'revision_status': task.revision_status,
        'task_status': task.task_status,
        'task_type': task.task_type,
        'title': task.title,
        'rigobot_repository_id': task.rigobot_repository_id,
        'attachments': [],
        'subtasks': task.subtasks,
        'telemetry': task.telemetry,
        'opened_at': self.bc.datetime.to_iso_string(task.opened_at) if task.opened_at else task.opened_at,
        'delivered_at': self.bc.datetime.to_iso_string(task.delivered_at) if task.delivered_at else task.delivered_at,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, 'delay', MagicMock())
    yield


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Auth
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__without_auth(self):
        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get without Task
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__without_task(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with one Task
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_one_task(self):
        model = self.bc.database.create(user=1, task=1, cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with two Task
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_two_task(self):
        model = self.bc.database.create(user=1, task=2, cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with querystring assets
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_query_string_assets(self):
        model = self.bc.database.create(user=1,
                                        task=[{
                                            'associated_slug': 'fine'
                                        }, {
                                            'associated_slug': 'super'
                                        }],
                                        cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task') + '?associated_slug=fine,super'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with querystring assets no results
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_query_string_assets_no_results(self):
        model = self.bc.database.create(user=1,
                                        task=[{
                                            'associated_slug': 'fine'
                                        }, {
                                            'associated_slug': 'super'
                                        }],
                                        cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task') + '?associated_slug=kenny'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with one Task but the other user
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_one_task__but_the_other_user(self):
        task = {'user_id': 2}
        model = self.bc.database.create(user=2, task=task, cohort=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with two Task but the other user
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_user_me_task__with_two_tasks__but_the_other_user(self):
        task = {'user_id': 2}
        model = self.bc.database.create(user=2, task=(2, task), cohort=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Delete
    """

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_delete_tasks_in_bulk_found_and_deleted(self):

        model = self.bc.database.create(user=1, task=2, cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task') + '?id=1,2'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_delete_tasks_in_bulk_tasks_not_found(self):

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

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
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_delete_task_in_bulk_associated_with_another_user(self):

        model = self.bc.database.create(user=2, task=2, cohort=1)
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
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Put
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_put__without_task(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = {}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'update-whout-list', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test__put__without_task__passing_list(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [], format='json')

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Put without Task, one item in body
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test__put__without_task__one_item_in_body(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = [{}]
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'missing=task-id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Put without Task, one item in body, with id
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test__put__without_task__one_item_in_body__with_id(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = [{'id': 1}]
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task, one item in body, with id
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_put_passing_taks_id(self):
        model = self.bc.database.create(user=1, task=2, cohort=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        response = self.client.put(url, [{'id': 1}, {'id': 2}], format='json')

        json = response.json()

        expected = [
            put_serializer(self, x, {'updated_at': self.bc.datetime.to_iso_string(UTC_NOW)}) for x in model.task
        ]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_put_passing_random_values_to_update_task(self):
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.bc.database.create(user=1, task=2, cohort=2)
        self.client.force_authenticate(model.user)

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
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = [
            put_serializer(self, model.task[x], {
                'updated_at': self.bc.datetime.to_iso_string(UTC_NOW),
                **data[x]
            }) for x in range(0, 2)
        ]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for x in range(0, 2):
            data[x]['cohort_id'] = data[x].pop('cohort')
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [{
            **self.bc.format.to_dict(model.task[x]),
            **data[x]
        } for x in range(0, 2)])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [
            call(model.user.id, 'assignment_status_updated', related_type='assignments.Task', related_id=x.id)
            for x in model.task if data[x.id - 1]['task_status'] != x.task_status
        ])

    """
    🔽🔽🔽 Put with Task, one item in body, passing revision_status
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test__put__with_task__one_item_in_body__passing_revision_status(self):
        statuses = ['APPROVED', 'REJECTED', 'IGNORED']
        for index in range(0, 3):
            current_status = statuses[index]
            next_status = statuses[index - 1 if index > 0 else 2]
            task = {'revision_status': current_status, 'task_status': 'DONE'}
            model = self.bc.database.create(user=1, task=task, cohort=1)
            self.client.force_authenticate(model.user)

            url = reverse_lazy('assignments:user_me_task')
            data = [{
                'id': index + 1,
                'revision_status': next_status,
            }]
            response = self.client.put(url, data, format='json')

            json = response.json()
            expected = {
                'detail': 'editing-revision-status-but-is-not-teacher-or-assistant',
                'status_code': 400,
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('assignments.Task'), [
                self.bc.format.to_dict(model.task),
            ])

            # teardown
            self.bc.database.delete('assignments.Task')
            self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task, one item in body, passing revision_status, teacher is auth
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send_robust', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test__put__with_task__one_item_in_body__passing_revision_status__teacher_token(self):
        statuses = ['APPROVED', 'REJECTED', 'IGNORED']
        for index in range(0, 3):
            current_status = statuses[index]
            next_status = statuses[index - 1 if index > 0 else 2]
            task = {'revision_status': current_status, 'task_status': 'DONE'}
            cohort_users = [
                {
                    'role': 'STUDENT',
                    'user_id': (index * 2) + 1,
                },
                {
                    'role': 'TEACHER',
                    'user_id': (index * 2) + 2,
                },
            ]
            with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
                model = self.bc.database.create(user=2, task=task, cohort_user=cohort_users, cohort=1)
            self.bc.request.authenticate(model.user[1])

            url = reverse_lazy('assignments:user_me_task')
            data = [{
                'id': index + 1,
                'revision_status': next_status,
            }]
            start = timezone.now()
            with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
                response = self.client.put(url, data, format='json')
            end = timezone.now()

            json = response.json()
            json = [
                x for x in json
                if self.bc.check.datetime_in_range(start, end, self.bc.datetime.from_iso_string(x['updated_at']))
                or x.pop('updated_at')
            ]
            expected = [put_serializer(self, model.task, data={'revision_status': next_status})]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('assignments.Task'), [
                {
                    **self.bc.format.to_dict(model.task),
                    'revision_status': next_status,
                },
            ])

            self.assertEqual(tasks.student_task_notification.delay.call_args_list, [call(index + 1)])
            self.assertEqual(tasks.teacher_task_notification.delay.call_args_list, [])

            self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [
                call(model.user[1].id,
                     'assignment_review_status_updated',
                     related_type='assignments.Task',
                     related_id=model.task.id),
            ])

            # teardown
            self.bc.database.delete('assignments.Task')
            tasks.student_task_notification.delay.call_args_list = []
            activity_tasks.add_activity.delay.call_args_list = []

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_with_data(self):
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.bc.database.create(user=1, task=2, cohort=2)

        self.client.force_authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        self.client.get(url)

        self.bc.check.calls(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'LanguageExtension', 'LookupExtension', 'PaginationExtension']),
        ])

        self.bc.check.calls(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=TaskCache, cache_per_user=True, paginate=True),
        ])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


def test_post__no_required_fields(client: capy.Client, database: capy.Database):
    url = reverse_lazy('assignments:user_me_task')

    model = database.create(user=1)
    client.force_authenticate(model.user)

    response = client.post(url)

    json = response.json()
    expected = [{
        'associated_slug': ['This field is required.'],
        'title': ['This field is required.'],
        'task_type': ['This field is required.'],
    }]

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert database.list_of('assignments.Task') == []


@pytest.mark.parametrize('task_type', [
    'PROJECT',
    'QUIZ',
    'LESSON',
    'EXERCISE',
])
def test_post__created(client: capy.Client, database: capy.Database, fake: capy.Fake, task_type: str,
                       utc_now: datetime):
    url = reverse_lazy('assignments:user_me_task')

    model = database.create(user=1, cohort=1, city=1, country=1)
    client.force_authenticate(model.user)

    data = {
        'associated_slug': fake.slug(),
        'title': fake.name(),
        'task_type': task_type,
        'cohort': 1,
    }
    response = client.post(url, data, format='json')

    json = response.json()
    del data['cohort']

    expected = [
        post_serializer(
            data={
                'created_at': utc_now.isoformat().replace('+00:00', 'Z'),
                'updated_at': utc_now.isoformat().replace('+00:00', 'Z'),
                **data,
            }),
    ]

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert database.list_of('assignments.Task') == [
        db_item(data),
    ]
