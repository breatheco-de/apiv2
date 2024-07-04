"""
Tasks Tests
"""

import logging
from unittest.mock import MagicMock, call, patch

import breathecode.certificate.actions as actions

from ...tasks import async_generate_certificate
from ..mixins import CertificateTestCase


class ActionCertificateGenerateOneCertificateTestCase(CertificateTestCase):
    """Tests action async_generate_certificate"""

    """
    🔽🔽🔽 CohortUser not found
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.certificate.actions.generate_certificate", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_async_generate_certificate__cohort_user_not_found(self):
        layout = "vanilla"
        async_generate_certificate(1, 1, layout)

        self.assertEqual(actions.generate_certificate.call_args_list, [])
        self.assertEqual(logging.Logger.info.call_args_list, [call("starting-generating-certificate")])
        self.assertEqual(logging.Logger.error.call_args_list, [call("cohort-user-not-found")])

    """
    🔽🔽🔽 Call generate_certificate successful
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.certificate.actions.generate_certificate", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_async_generate_certificate_with_user_role_student(self):
        cohort_user = {"role": "STUDENT"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort_user=cohort_user)
            logging.Logger.info.call_args_list = []

        layout = "vanilla"
        async_generate_certificate(1, 1, layout)
        self.assertEqual(
            actions.generate_certificate.call_args_list,
            [
                call(model.user, model.cohort, "vanilla"),
            ],
        )

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("starting-generating-certificate"),
                call("generating-certificate"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 Call generate_certificate raise a exception
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.certificate.actions.generate_certificate", MagicMock(side_effect=Exception()))
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_async_generate_certificate_with_user_role_teacher(self):
        cohort_user = {"role": "STUDENT"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort_user=cohort_user)
            logging.Logger.info.call_args_list = []

        layout = "vanilla"
        async_generate_certificate(1, 1, layout)
        self.assertEqual(
            actions.generate_certificate.call_args_list,
            [
                call(model.user, model.cohort, "vanilla"),
            ],
        )

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("starting-generating-certificate"),
                call("generating-certificate"),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("error-generating-certificate", exc_info=True),
            ],
        )
