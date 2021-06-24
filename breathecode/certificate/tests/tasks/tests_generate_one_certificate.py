"""
Tasks tests
"""
from unittest.mock import patch, call
from ...tasks import generate_one_certificate
from ..mixins.new_certificate_test_case import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_certificate_screenshot_mock,
    apply_remove_certificate_screenshot_mock,
)


class ActionCertificateGenerateOneCertificateTestCase(CertificateTestCase):
    """Tests action generate_one_certificate"""
    def test_generate_one_certificate_bad_request(self):
        """generate_one_certificate cant create the certificate"""
        with patch("breathecode.certificate.actions.generate_certificate"
                   ) as mock:
            generate_one_certificate(1, 1)

        self.assertEqual(mock.call_args_list, [])

    def test_generate_one_certificate_with_user_role_student(self):
        """Good request for generate_one_certificate"""
        cohort_user_kwargs = {"role": "STUDENT"}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     cohort_user_kwargs=cohort_user_kwargs)
        with patch("breathecode.certificate.actions.generate_certificate"
                   ) as mock:
            generate_one_certificate(1, 1)
        self.assertEqual(mock.call_args_list, [call(model.user, model.cohort)])

    def test_generate_one_certificate_with_user_role_teacher(self):
        """bad request with user role teacher"""
        cohort_user_kwargs = {"role": "TEACHER"}
        self.generate_models(user=True,
                             cohort=True,
                             cohort_user=True,
                             cohort_user_kwargs=cohort_user_kwargs)
        with patch("breathecode.certificate.actions.generate_certificate"
                   ) as mock:
            generate_one_certificate(1, 1)
        self.assertEqual(mock.call_args_list, [])
