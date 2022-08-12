"""
Test /answer
"""
from django.utils import timezone
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.assignments import tasks

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
        **data,
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
        expected = [get_serializer(self, model.task, model.user)]

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
        expected = [get_serializer(self, task, model.user) for task in model.task]

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
    🔽🔽🔽 Put without Task
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__without_task__passing_dict(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = {}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'update-whout-list', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__without_task__passing_list(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = []
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Put without Task, one item in body
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__without_task__one_item_in_body(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = [{}]
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'missing=task-id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Put without Task, one item in body, with id
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__without_task__one_item_in_body__with_id(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = [{'id': 1}]
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Put with Task, one item in body, with id
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__with_task__one_item_in_body__with_id(self):
        model = self.bc.database.create(user=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:user_me_task')
        data = [{'id': 1}]
        start = timezone.now()
        response = self.client.put(url, data, format='json')
        end = timezone.now()

        json = response.json()
        json = [
            x for x in json
            if self.bc.check.datetime_in_range(start, end, self.bc.datetime.from_iso_string(x['updated_at']))
            or x.pop('updated_at')
        ]
        expected = [put_serializer(self, model.task)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Put with Task, one item in body, passing revision_status
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test__put__with_task__one_item_in_body__passing_revision_status(self):
        statuses = ['APPROVED', 'REJECTED', 'IGNORED']
        for index in range(0, 3):
            current_status = statuses[index]
            next_status = statuses[index - 1 if index > 0 else 2]
            task = {'revision_status': current_status, 'task_status': 'DONE'}
            model = self.bc.database.create(user=1, task=task)
            self.bc.request.authenticate(model.user)

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

    """
    🔽🔽🔽 Put with Task, one item in body, passing revision_status, teacher is auth
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
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
            model = self.bc.database.create(user=2, task=task, cohort_user=cohort_users)
            self.bc.request.authenticate(model.user[1])

            url = reverse_lazy('assignments:user_me_task')
            data = [{
                'id': index + 1,
                'revision_status': next_status,
            }]
            start = timezone.now()
            response = self.client.put(url, data, format='json')
            end = timezone.now()

            json = response.json()
            json = [
                x for x in json if self.bc.check.datetime_in_range(
                    start, end, self.bc.datetime.from_iso_string(x['updated_at'])) or x.pop('updated_at')
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

            # teardown
            self.bc.database.delete('assignments.Task')
            tasks.student_task_notification.delay.call_args_list = []
