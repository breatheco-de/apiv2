"""
Test /cohort/user
"""
from unittest.mock import MagicMock, call, patch
from breathecode.admissions.models import CohortUser
from breathecode.admissions.admin import add_student_tag_to_active_campaign
from django.http.request import HttpRequest
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 With zero CohortUser
    """
    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    def test_add_student_tag_to_active_campaign__zero_cohort_users(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student

        request = HttpRequest()
        queryset = CohortUser.objects.all()

        add_student_tag_to_active_campaign(None, request, queryset)

        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [])

    """
    🔽🔽🔽 With one CohortUser
    """

    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    def test_add_student_tag_to_active_campaign__one_cohort_user(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student

        model = self.generate_models(cohort_user=True)

        request = HttpRequest()
        queryset = CohortUser.objects.all()

        add_student_tag_to_active_campaign(None, request, queryset)

        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [
            call(model.user.id, model.cohort.id, model.cohort.academy.id),
        ])

    """
    🔽🔽🔽 With two CohortUser
    """

    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    def test_add_student_tag_to_active_campaign__two_cohort_users(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student

        model1 = self.generate_models(cohort_user=True)
        model2 = self.generate_models(cohort_user=True)

        request = HttpRequest()
        queryset = CohortUser.objects.all()

        add_student_tag_to_active_campaign(None, request, queryset)

        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [
            call(model1.user.id, model1.cohort.id, model1.cohort.academy.id),
            call(model2.user.id, model2.cohort.id, model2.cohort.academy.id),
        ])
