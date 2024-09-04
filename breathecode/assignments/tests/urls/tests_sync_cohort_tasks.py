"""
Test /answer
"""

from unittest.mock import MagicMock, call, patch

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.assignments import tasks

from ..mixins import AssignmentsTestCase


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr(tasks.sync_cohort_user_tasks, "delay", MagicMock())
    yield


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Auth
    """

    def test_sync_cohort_tasks__without_auth(self):
        url = reverse_lazy("assignments:sync_cohort_tasks", kwargs={"cohort_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.bc.check.calls(tasks.sync_cohort_user_tasks.delay.call_args_list, [])

    def test_sync_cohort_tasks__without_capability(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("assignments:sync_cohort_tasks", kwargs={"cohort_id": 1})
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_assignment for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bc.check.calls(tasks.sync_cohort_user_tasks.delay.call_args_list, [])

    def test_sync_cohort_tasks__with_no_cohort(self):

        model = self.bc.database.create(profile_academy=1, role=1, capability="crud_assignment")
        self.client.force_authenticate(model.user)

        url = reverse_lazy("assignments:sync_cohort_tasks", kwargs={"cohort_id": 2})
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        expected = {"detail": "cohort-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(tasks.sync_cohort_user_tasks.delay.call_args_list, [])

    def test_sync_cohort_tasks__with_one_cohort_user(self):

        model = self.bc.database.create(profile_academy=1, role=1, capability="crud_assignment", cohort_user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("assignments:sync_cohort_tasks", kwargs={"cohort_id": 1})
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        expected = {"message": "tasks-syncing"}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(tasks.sync_cohort_user_tasks.delay.call_args_list, [call(1)])

    def test_sync_cohort_tasks__with_many_cohort_users(self):

        model = self.bc.database.create(profile_academy=1, role=1, capability="crud_assignment", cohort_user=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("assignments:sync_cohort_tasks", kwargs={"cohort_id": 1})
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        expected = {"message": "tasks-syncing"}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(tasks.sync_cohort_user_tasks.delay.call_args_list, [call(1), call(2), call(3)])
