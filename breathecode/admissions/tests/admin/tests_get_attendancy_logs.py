"""
Test /cohort/user
"""

import random
from unittest.mock import MagicMock, call, patch
from breathecode.admissions.models import Cohort
from breathecode.activity import tasks
from breathecode.admissions.admin import get_attendancy_logs
from django.http.request import HttpRequest
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 With zero Cohort
    """

    @patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock())
    def test_without_cohorts(self):
        request = HttpRequest()
        queryset = Cohort.objects.all()

        get_attendancy_logs(None, request, queryset)

        self.assertEqual(tasks.get_attendancy_log.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock())
    def test_with_many_cohorts(self):
        how_many = random.randint(2, 5)
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            self.bc.database.create(cohort=how_many)
        request = HttpRequest()
        queryset = Cohort.objects.all()

        get_attendancy_logs(None, request, queryset)

        self.assertEqual(tasks.get_attendancy_log.delay.call_args_list, [call(n) for n in range(1, how_many + 1)])
