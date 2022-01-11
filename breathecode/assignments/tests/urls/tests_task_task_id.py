from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AssignmentsTestCase

# Create your tests here.


class TaskTestSuite(AssignmentsTestCase):
    def test_put_needs_associated_slug_and_title(self):
        """Test /task with needs to have data present containing associated slug and title"""

        model = self.generate_models(task=True, authenticate=True)
        url = reverse_lazy('assignments:task_id', kwargs={
            'task_id': model.task.id,
        })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'associated_slug': ['This field is required.'], 'title': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_status_and_revision_status_pending_accepted(self):
        """Test /task with task_status = pending and revision_status = pending should pass"""

        model = self.generate_models(task=True, authenticate=True)
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
        self.assertEqual(self.all_task_dict(), [{
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
