from unittest.mock import MagicMock, call, patch
from ..mixins import CertificateTestCase
import breathecode.certificate.signals as signals
import breathecode.certificate.tasks as tasks


class AcademyEventTestSuite(CertificateTestCase):
    """
    🔽🔽🔽 Status ERROR
    """
    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_error(self):
        user_specialty = {'status': 'ERROR'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PENDING
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_pending(self):
        user_specialty = {'status': 'PENDING'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])
