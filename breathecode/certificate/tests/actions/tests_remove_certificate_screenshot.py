"""
Tasks tests
"""

from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

import breathecode.certificate.signals as signals
from breathecode.services.google_cloud import File, Storage

from ...actions import remove_certificate_screenshot
from ...models import UserSpecialty
from ..mixins import CertificateTestCase


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.File.bucket", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.file_name", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.blob", PropertyMock(return_value=1), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.upload", MagicMock())
    monkeypatch.setattr("breathecode.services.google_cloud.File.delete", MagicMock())
    monkeypatch.setattr(
        "breathecode.services.google_cloud.File.url", MagicMock(return_value="https://xyz/hardcoded_url")
    )


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action remove_certificate_screenshot"""

    """
    🔽🔽🔽 UserSpecialty not exists
    """

    def test_remove_certificate_screenshot_with_invalid_id(self):
        """remove_certificate_screenshot don't call open in development environment"""

        with self.assertRaisesMessage(UserSpecialty.DoesNotExist, "UserSpecialty matching query does not exist."):
            remove_certificate_screenshot(1)

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With preview_url as a empty string
    """

    def test_remove_certificate_screenshot__with_preview_url_as_empty_string(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": ""}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertFalse(result)
        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                },
            ],
        )

        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With preview_url as a None
    """

    def test_remove_certificate_screenshot__with_preview_url_as_none(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": None}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertFalse(result)
        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                },
            ],
        )

        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )
        self.assertEqual(File.delete.call_args_list, [])

    """
    🔽🔽🔽 With a properly preview_url
    """

    def test_remove_certificate_screenshot__with_a_properly_preview_url(self):
        """remove_certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": "https://xyz/hardcoded_url"}
        model = self.generate_models(user_specialty=user_specialty)

        result = remove_certificate_screenshot(1)

        self.assertTrue(result)
        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                    "preview_url": "",
                },
            ],
        )

        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Save
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )
        self.assertEqual(File.delete.call_args_list, [call()])
