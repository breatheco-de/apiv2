"""
Admin tests
"""
from unittest.mock import patch, call

from django.http.request import HttpRequest
from breathecode.tests.mocks import (
    DJANGO_CONTRIB_PATH,
    DJANGO_CONTRIB_INSTANCES,
    apply_django_contrib_messages_mock,
)
from ...admin import cohort_bulk_certificate
from ...models import Certificate, Cohort
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_generate_certificate_mock,
)

class AdminCohortBulkCertificateTestCase(CertificateTestCase):
    """Tests action cohort_bulk_certificate"""
    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_without_cohort(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        # model = self.generate_models()

        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
            ' generation')])
        self.assertEqual(mock.error.call_args_list, [])

        self.assertEqual(self.count_cohort(), 0)
        self.assertEqual(self.count_certificate(), 0)

    # # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    # @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    # @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    # def test_cohort_bulk_certificate_with_cohort(self):
    #     """cohort_bulk_certificate don't call open in development environment"""
    #     request = HttpRequest()
    #     mock = DJANGO_CONTRIB_INSTANCES['messages']
    #     mock.success.call_args_list = []
    #     mock.error.call_args_list = []

    #     model = self.generate_models()

    #     self.assertEqual(self.count_certificate(), 0)
    #     self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

    #     self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
    #         ' generation')])
    #     self.assertEqual(mock.error.call_args_list, [])

    #     self.assertEqual(self.count_cohort(), 1)
    #     self.assertEqual(self.count_certificate(), 1)
    #     assert False
