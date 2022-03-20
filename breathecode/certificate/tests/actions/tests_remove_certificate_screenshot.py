"""
Tasks tests
"""
from unittest.mock import MagicMock, PropertyMock, call, patch
from ...actions import remove_certificate_screenshot
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
import breathecode.certificate.signals as signals
from breathecode.services.google_cloud import Storage, File


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action remove_certificate_screenshot"""
    """
    🔽🔽🔽 UserSpecialty not exists
    """
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(return_value=1),
                    upload=MagicMock(),
                    delete=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
    def test_remove_certificate_screenshot_with_invalid_id(self):
        """remove_certificate_screenshot don't call open in development environment"""

        with self.assertRaisesMessage(UserSpecialty.DoesNotExist,
                                      'UserSpecialty matching query does not exist.'):
            remove_certificate_screenshot(1)

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With preview_url as a empty string
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(return_value=1),
                    upload=MagicMock(),
                    delete=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
    def test_remove_certificate_screenshot__with_preview_url_as_empty_string(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {'preview_url': ''}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertFalse(result)
        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [
            {
                **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
            },
        ])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With preview_url as a None
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(return_value=1),
                    upload=MagicMock(),
                    delete=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
    def test_remove_certificate_screenshot__with_preview_url_as_none(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {'preview_url': None}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertFalse(result)
        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [
            {
                **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
            },
        ])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With a properly preview_url
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(return_value=1),
                    upload=MagicMock(),
                    delete=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
    def test_remove_certificate_screenshot__with_a_properly_preview_url(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {'preview_url': 'https://xyz/hardcoded_url'}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertTrue(result)
        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [
            {
                **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                'preview_url':
                '',
            },
        ])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])
        self.assertEqual(File.delete.call_args_list, [call()])
