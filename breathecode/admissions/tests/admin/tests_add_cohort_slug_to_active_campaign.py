"""
Test /cohort/user
"""

from unittest.mock import MagicMock, call, patch
from breathecode.admissions.models import Cohort
from breathecode.admissions.admin import add_cohort_slug_to_active_campaign
from django.http.request import HttpRequest
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 With zero Cohort
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_add_cohort_slug_to_active_campaign__zero_cohorts(self):
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        request = HttpRequest()
        queryset = Cohort.objects.all()

        add_cohort_slug_to_active_campaign(None, request, queryset)

        self.assertEqual(add_cohort_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 With one Cohort
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_add_cohort_slug_to_active_campaign__one_cohort(self):
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        model = self.generate_models(cohort=True)

        request = HttpRequest()
        queryset = Cohort.objects.all()

        add_cohort_slug_to_active_campaign(None, request, queryset)

        self.assertEqual(
            add_cohort_slug_as_acp_tag.delay.call_args_list,
            [
                call(model.cohort.id, model.cohort.academy.id),
            ],
        )

    """
    🔽🔽🔽 With two Cohort
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_add_cohort_slug_to_active_campaign__two_cohorts(self):
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        model1 = self.generate_models(cohort=True)
        model2 = self.generate_models(cohort=True)

        request = HttpRequest()
        queryset = Cohort.objects.all()

        add_cohort_slug_to_active_campaign(None, request, queryset)

        self.assertEqual(
            add_cohort_slug_as_acp_tag.delay.call_args_list,
            [
                call(model1.cohort.id, model1.cohort.academy.id),
                call(model2.cohort.id, model2.cohort.academy.id),
            ],
        )
