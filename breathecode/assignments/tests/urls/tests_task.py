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

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without ProfileAcademy
    """

    def test_task__without_profile_academy(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'without-profile-academy',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get without Task
    """

    def test_task__without_data(self):
        model = self.bc.database.create(user=1, profile_academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    """
    🔽🔽🔽 Get with Task
    """

    def test_task__one_task__cohort_null(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    """
    🔽🔽🔽 Get with two Task
    """

    def test_task__two_tasks(self):
        model = self.bc.database.create(profile_academy=1, task=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query academy
    """

    def test_task__query_academy__found_zero__academy_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?academy={model.academy.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_one__cohort_null(self):
        model = self.bc.database.create(profile_academy=1, task=1, skip_cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_academy__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?academy={model.academy.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_academy__found_two__cohort_null(self):
        model = self.bc.database.create(profile_academy=1, task=2, skip_cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?academy=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query user
    """

    def test_task__query_user__found_zero__user_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=2'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_user__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_user__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?user=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_user__found_two__related_to_two_users(self):
        tasks = [{'user_id': 1}, {'user_id': 2}]
        model = self.bc.database.create(profile_academy=1, user=2, task=tasks, cohort=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task') + '?user=1,2'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user[task.id - 1]) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query cohort
    """

    def test_task__query_cohort__id__found_zero__cohort_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?cohort=2'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_cohort__slug__found_zero__cohort_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?cohort=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_cohort__id__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?cohort=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_cohort__slug__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?cohort={model.cohort.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_cohort__id__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?cohort=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_cohort__slug__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?cohort={model.cohort.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_cohort__id__found_two__related_to_two_users(self):
        tasks = [{'cohort_id': 1}, {'cohort_id': 2}]
        model = self.bc.database.create(profile_academy=1, user=1, task=tasks, cohort=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?cohort=1,2'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_cohort__slug__found_two__related_to_two_users(self):
        tasks = [{'cohort_id': 1}, {'cohort_id': 2}]
        model = self.bc.database.create(profile_academy=1, user=1, task=tasks, cohort=2)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?cohort={model.cohort[0].slug},{model.cohort[1].slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query stu_cohort
    """

    def test_task__query_stu_cohort__id__found_zero__cohort_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?stu_cohort=2'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_stu_cohort__slug__found_zero__cohort_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?stu_cohort=they-killed-kenny'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_stu_cohort__id__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1, cohort_user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?stu_cohort=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_stu_cohort__slug__found_one(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1, cohort_user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?stu_cohort={model.cohort.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_stu_cohort__id__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1, cohort_user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?stu_cohort=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_stu_cohort__slug__found_two(self):
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1, cohort_user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?stu_cohort={model.cohort.slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_stu_cohort__id__found_two__related_to_two_users(self):
        tasks = [{'cohort_id': 1, 'user_id': 1}, {'cohort_id': 2, 'user_id': 2}]
        cohort_users = [{'cohort_id': 1, 'user_id': 1}, {'cohort_id': 2, 'user_id': 2}]
        model = self.bc.database.create(profile_academy=1,
                                        user=2,
                                        task=tasks,
                                        cohort=2,
                                        cohort_user=cohort_users)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task') + '?stu_cohort=1,2'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user[task.id - 1]) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_stu_cohort__slug__found_two__related_to_two_users(self):
        tasks = [{'cohort_id': 1, 'user_id': 1}, {'cohort_id': 2, 'user_id': 2}]
        cohort_users = [{'cohort_id': 1, 'user_id': 1}, {'cohort_id': 2, 'user_id': 2}]
        model = self.bc.database.create(profile_academy=1,
                                        user=2,
                                        task=tasks,
                                        cohort=2,
                                        cohort_user=cohort_users)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task') + f'?stu_cohort={model.cohort[0].slug},{model.cohort[1].slug}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user[task.id - 1]) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query edu_status
    """

    def test_task__query_edu_status__found_zero__edu_status_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?edu_status=ACTIVE'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_edu_status__found_one(self):
        cohort_user = {'user_id': 1, 'educational_status': 'ACTIVE'}
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1, cohort_user=cohort_user)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?edu_status={model.cohort_user.educational_status}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_edu_status__found_two(self):
        cohort_user = {'user_id': 1, 'educational_status': 'ACTIVE'}
        model = self.bc.database.create(profile_academy=1, task=2, cohort=1, cohort_user=cohort_user)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?edu_status={model.cohort_user.educational_status}'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_edu_status__found_two__related_to_two_edu_status(self):
        tasks = [{'user_id': 1, 'cohort_id': 1}, {'user_id': 2, 'cohort_id': 2}]
        cohort_users = [
            {
                'user_id': 1,
                'educational_status': 'ACTIVE',
            },
            {
                'user_id': 2,
                'educational_status': 'DROPPED',
            },
        ]
        model = self.bc.database.create(profile_academy=1,
                                        user=2,
                                        task=tasks,
                                        cohort=2,
                                        cohort_user=cohort_users)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('assignments:task') + f'?edu_status=ACTIVE,DROPPED'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user[task.id - 1]) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query teacher
    """

    def test_task__query_teacher__found_zero__academy_not_exists(self):
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?teacher=1'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_teacher__found_one(self):
        cohort_users = [
            {
                'role': 'STUDENT',
                'user_id': 1,
                'cohort_id': 1,
            },
            {
                'role': 'TEACHER',
                'user_id': 1,
                'cohort_id': 1,
            },
        ]
        model = self.bc.database.create(profile_academy=1, task=1, cohort=1, cohort_user=cohort_users)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?teacher=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_teacher__found_two(self):
        tasks = [{'user_id': 1, 'cohort_id': 1}, {'user_id': 1, 'cohort_id': 2}]
        cohort_users = [
            {
                'role': 'STUDENT',
                'user_id': 1,
                'cohort_id': 1,
            },
            {
                'role': 'STUDENT',
                'user_id': 1,
                'cohort_id': 2,
            },
            {
                'role': 'TEACHER',
                'user_id': 1,
                'cohort_id': 1,
            },
            {
                'role': 'TEACHER',
                'user_id': 1,
                'cohort_id': 2,
            },
        ]
        model = self.bc.database.create(profile_academy=1,
                                        task=tasks,
                                        user=1,
                                        cohort=2,
                                        cohort_user=cohort_users)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?teacher=1'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query task_status
    """

    def test_task__query_task_status__found_zero__task_status_not_exists(self):
        task = {'task_status': 'PENDING'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_status=DONE'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_task_status__found_one(self):
        task = {'user_id': 1, 'task_status': 'DONE'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_status=DONE'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_task_status__found_two(self):
        tasks = [{'user_id': 1, 'task_status': 'DONE'}, {'user_id': 1, 'task_status': 'DONE'}]
        model = self.bc.database.create(profile_academy=1, task=tasks)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_status=DONE'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_task_status__found_two__related_to_two_task_status(self):
        tasks = [{'task_status': 'DONE'}, {'task_status': 'PENDING'}]
        model = self.bc.database.create(profile_academy=1, user=1, task=tasks)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?task_status=DONE,PENDING'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query revision_status
    """

    def test_task__query_revision_status__found_zero__revision_status_not_exists(self):
        task = {'revision_status': 'PENDING'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?revision_status=APPROVED'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_revision_status__found_one(self):
        task = {'user_id': 1, 'revision_status': 'APPROVED'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?revision_status=APPROVED'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_revision_status__found_two(self):
        tasks = [{'user_id': 1, 'revision_status': 'APPROVED'}, {'user_id': 1, 'revision_status': 'APPROVED'}]
        model = self.bc.database.create(profile_academy=1, task=tasks)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?revision_status=APPROVED'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_revision_status__found_two__related_to_two_revision_status(self):
        tasks = [{'revision_status': 'APPROVED'}, {'revision_status': 'PENDING'}]
        model = self.bc.database.create(profile_academy=1, user=1, task=tasks)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?revision_status=APPROVED,PENDING'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    """
    🔽🔽🔽 Query task_type
    """

    def test_task__query_task_type__found_zero__task_type_not_exists(self):
        task = {'task_type': 'QUIZ'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_type=PROJECT'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_task_type__found_one(self):
        task = {'user_id': 1, 'task_type': 'PROJECT'}
        model = self.bc.database.create(profile_academy=1, task=task)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_type=PROJECT'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.task, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])

    def test_task__query_task_type__found_two(self):
        tasks = [{'user_id': 1, 'task_type': 'PROJECT'}, {'user_id': 1, 'task_type': 'PROJECT'}]
        model = self.bc.database.create(profile_academy=1, task=tasks)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + '?task_type=PROJECT'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))

    def test_task__query_revision_status__found_two__related_to_two_revision_status(self):
        tasks = [{'task_type': 'PROJECT'}, {'task_type': 'QUIZ'}]
        model = self.bc.database.create(profile_academy=1, user=1, task=tasks)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:task') + f'?task_type=PROJECT,QUIZ'
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, task, model.user) for task in model.task]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), self.bc.format.to_dict(model.task))
