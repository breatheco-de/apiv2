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
    def test_task_id__without_auth(self):
        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without Task
    """

    def test_task_id__without_task(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get with Task
    """

    def test_task_id__with_one_task(self):
        model = self.bc.database.create(user=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
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
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Get with Task but the other user
    """

    def test_task_id__with_one_task__but_the_other_user(self):
        task = {'user_id': 2}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Put without Task
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__without_tasks(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'task-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__bad_fields(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(user=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'associated_slug': ['This field is required.'], 'title': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(user=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {'associated_slug': 'they-killed-kenny', 'title': 'They killed kenny'}
        start = self.bc.datetime.now()
        response = self.client.put(url, data, format='json')
        end = self.bc.datetime.now()

        json = response.json()

        updated_at = self.bc.datetime.from_iso_string(json['updated_at'])
        self.bc.check.datetime_in_range(start, end, updated_at)
        del json['updated_at']

        expected = {
            'github_url': model.task.github_url,
            'cohort': model.task.cohort,
            'created_at': self.bc.datetime.to_iso_string(model.task.created_at),
            'id': model.task.id,
            'description': model.task.description,
            'live_url': model.task.live_url,
            'revision_status': model.task.revision_status,
            'task_status': model.task.task_status,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [{
            **self.bc.format.to_dict(model.task),
            **data,
        }])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task of other user passing task_status
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_task_status(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'task_status': 'PENDING', 'user_id': 2}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'task_status': 'DONE',
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'put-task-status-of-other-user', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task of other user passing live_url
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_live_url(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'live_url': 'PENDING', 'user_id': 2}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'live_url': 'DONE',
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'put-live-url-of-other-user', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task of other user passing github_url
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_github_url(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'github_url': 'PENDING', 'user_id': 2}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'github_url': 'DONE',
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'put-github-url-of-other-user', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put with Task of other user passing revision_status
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_revision_status(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'revision_status': 'PENDING', 'user_id': 2, 'task_status': 'DONE'}
        model = self.bc.database.create(user=2, task=task)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'revision_status': 'APPROVED',
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'editing-revision-status-but-is-not-teacher-or-assistant', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_revision_status__teacher_auth(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'revision_status': 'PENDING', 'user_id': 1, 'task_status': 'DONE'}
        cohort_users = [{'role': 'STUDENT', 'user_id': 1}, {'role': 'TEACHER', 'user_id': 2}]
        model = self.bc.database.create(user=2, task=task, cohort=1, cohort_user=cohort_users)
        self.bc.request.authenticate(model.user[1])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'revision_status': 'APPROVED',
        }
        start = self.bc.datetime.now()
        response = self.client.put(url, data, format='json')
        end = self.bc.datetime.now()

        json = response.json()
        updated_at = self.bc.datetime.from_iso_string(json['updated_at'])
        self.bc.check.datetime_in_range(start, end, updated_at)
        del json['updated_at']

        expected = {
            'github_url': model.task.github_url,
            'cohort': model.task.cohort.id,
            'created_at': self.bc.datetime.to_iso_string(model.task.created_at),
            'id': model.task.id,
            'description': model.task.description,
            'live_url': model.task.live_url,
            'revision_status': model.task.revision_status,
            'task_status': model.task.task_status,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [{
            **self.bc.format.to_dict(model.task),
            **data,
        }])

        self.assertEqual(student_task_notification.delay.call_args_list, [call(1)])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_id__put__with_one_task__with_revision_status__staff_auth(self):
        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        task = {'revision_status': 'PENDING', 'user_id': 1, 'task_status': 'DONE'}
        cohort_user = {'role': 'STUDENT', 'user_id': 1}
        profile_academy = {'user_id': 2}
        model = self.bc.database.create(user=2,
                                        task=task,
                                        cohort=1,
                                        cohort_user=cohort_user,
                                        profile_academy=profile_academy)
        self.bc.request.authenticate(model.user[1])

        url = reverse_lazy('assignments:task_id', kwargs={'task_id': 1})
        data = {
            'associated_slug': 'they-killed-kenny',
            'title': 'They killed kenny',
            'revision_status': 'APPROVED',
        }
        start = self.bc.datetime.now()
        response = self.client.put(url, data, format='json')
        end = self.bc.datetime.now()

        json = response.json()
        updated_at = self.bc.datetime.from_iso_string(json['updated_at'])
        self.bc.check.datetime_in_range(start, end, updated_at)
        del json['updated_at']

        expected = {
            'github_url': model.task.github_url,
            'cohort': model.task.cohort.id,
            'created_at': self.bc.datetime.to_iso_string(model.task.created_at),
            'id': model.task.id,
            'description': model.task.description,
            'live_url': model.task.live_url,
            'revision_status': model.task.revision_status,
            'task_status': model.task.task_status,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [{
            **self.bc.format.to_dict(model.task),
            **data,
        }])

        self.assertEqual(student_task_notification.delay.call_args_list, [call(1)])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    """
    🔽🔽🔽 Put prevent mark task as done if it is not delivered
    """

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_status_pending_and_revision_status_pending(self):
        """Test /task with task_status = pending and revision_status = pending should pass"""

        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(task=1, user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={
            'task_id': model.task.id,
        })
        data = {'associated_slug': 'hello', 'title': 'hello'}
        response = self.client.put(url, data)
        json = response.json()
        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']
        expected = {
            'id': 1,
            'associated_slug': 'hello',
            'title': 'hello',
            'task_status': 'PENDING',
            'revision_status': 'PENDING',
            'github_url': None,
            'live_url': None,
            'description': model.task.description,
            'cohort': None
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [{
            'id': 1,
            'associated_slug': 'hello',
            'title': 'hello',
            'task_status': 'PENDING',
            'revision_status': 'PENDING',
            'task_type': model.task.task_type,
            'github_url': None,
            'live_url': None,
            'description': model.task.description,
            'cohort_id': None,
            'user_id': 1
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_status_pending_and_revision_status_approved(self):
        """Test /task with task_status = pending and revision_status = approved should fail"""

        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(task=1, user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={
            'task_id': model.task.id,
        })

        data = {
            'associated_slug': 'hello',
            'title': 'hello',
            'revision_status': 'APPROVED',
        }

        response = self.client.put(url, data)
        json = response.json()

        expected = {'detail': 'task-marked-approved-when-pending', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.student_task_notification', MagicMock())
    @patch('breathecode.assignments.tasks.teacher_task_notification', MagicMock())
    def test_task_status_pending_and_revision_status_approved_both(self):
        """Test /task with task_status = pending and revision_status = approved should fail"""

        from breathecode.assignments.tasks import student_task_notification
        from breathecode.assignments.tasks import teacher_task_notification

        model = self.bc.database.create(task=1, user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task_id', kwargs={
            'task_id': model.task.id,
        })

        data = {
            'associated_slug': 'hello',
            'title': 'hello',
            'task_status': 'DONE',
            'revision_status': 'APPROVED'
        }

        response = self.client.put(url, data)
        json = response.json()

        expected = {'detail': 'task-marked-approved-when-pending', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

        self.assertEqual(student_task_notification.delay.call_args_list, [])
        self.assertEqual(teacher_task_notification.delay.call_args_list, [])
