"""
Tasks tests
"""

import os
from unittest.mock import MagicMock, PropertyMock, call, patch
from urllib.parse import urlencode

import pytest
import requests

import breathecode.certificate.signals as signals
from breathecode.services.google_cloud import File, Storage
from breathecode.tests.mocks import apply_requests_get_mock

from ...actions import certificate_screenshot
from ...models import UserSpecialty
from ..mixins import CertificateTestCase

token = "12345a67890b12345c67890d"
query_string = urlencode(
    {
        "key": os.environ.get("SCREENSHOT_MACHINE_KEY", "00000"),
        "url": f"https://certificate.4geeks.com/preview/{token}",
        "dimension": "1024x707",
        "device": "desktop",
        "delay": 1000,
        "cacheLimit": "0",
    }
)


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCREENSHOT_MACHINE_KEY", "00000")


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action certificate_screenshot"""

    """
    🔽🔽🔽 Zero UserSpecialty
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (200, f"https://api.screenshotmachine.com?{query_string}", "mailgun response"),
            ]
        ),
    )
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, f"https://api.screenshotmachine.com?{query_string}")]))
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    def test_certificate_screenshot__with_invalid_id(self):
        """certificate_screenshot don't call open in development environment"""

        with self.assertRaisesMessage(UserSpecialty.DoesNotExist, "UserSpecialty matching query does not exist."):
            certificate_screenshot(1)

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])
        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])

    """
    🔽🔽🔽 Invalid preview_url, equal to ''
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (200, f"https://api.screenshotmachine.com?{query_string}", "mailgun response"),
            ]
        ),
    )
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, f"https://api.screenshotmachine.com?{query_string}")]))
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    def test_certificate_screenshot__with_invalid_preview_url__equal_to_empty_string(self):
        """certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": "", "token": token}
        model = self.bc.database.create(user_specialty=user_specialty)

        certificate_screenshot(1)

        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                    "preview_url": "https://xyz/hardcoded_url",
                },
            ],
        )

        assert requests.get.call_args_list == [
            call(f"https://api.screenshotmachine.com?{query_string}", timeout=25, stream=True),
        ]

        assert signals.user_specialty_saved.send_robust.call_args_list == [
            # Mixer
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            # Save
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ]

        assert File.upload.call_args_list == [call(b"mailgun response", public=True)]
        assert File.url.call_args_list == [call()]

    """
    🔽🔽🔽 Invalid preview_url, equal to None
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (200, f"https://api.screenshotmachine.com?{query_string}", "mailgun response"),
            ]
        ),
    )
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    def test_certificate_screenshot__with_invalid_preview_url__equal_to_none(self):
        """certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": None, "token": token}
        model = self.bc.database.create(user_specialty=user_specialty)

        certificate_screenshot(1)

        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                    "preview_url": "https://xyz/hardcoded_url",
                },
            ],
        )

        assert requests.get.call_args_list == [
            call(f"https://api.screenshotmachine.com?{query_string}", timeout=25, stream=True),
        ]

        assert signals.user_specialty_saved.send_robust.call_args_list == [
            # Mixer
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            # Save
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ]

        assert File.upload.call_args_list == [call(b"mailgun response", public=True)]
        assert File.url.call_args_list == [call()]

    """
    🔽🔽🔽 Invalid preview_url, the object exists in gcloud
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (200, f"https://api.screenshotmachine.com?{query_string}", "mailgun response"),
            ]
        ),
    )
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(return_value=1),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    def test_certificate_screenshot__with_invalid_preview_url__the_objects_exists_in_gcloud(self):
        """certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": None, "token": token}
        model = self.bc.database.create(user_specialty=user_specialty)

        certificate_screenshot(1)

        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                    "preview_url": "https://xyz/hardcoded_url",
                },
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Save
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )

        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [call()])

    """
    🔽🔽🔽 Correct preview_url
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (200, f"https://api.screenshotmachine.com?{query_string}", "mailgun response"),
            ]
        ),
    )
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(return_value=1),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    def test_certificate_screenshot__with_correct_preview_url(self):
        """certificate_screenshot don't call open in development environment"""

        user_specialty = {"preview_url": "https://xyz/hardcoded_url", "token": token}
        model = self.bc.database.create(user_specialty=user_specialty)

        certificate_screenshot(1)

        self.assertEqual(
            self.bc.database.list_of("certificate.UserSpecialty"),
            [
                {
                    **self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty)),
                    "preview_url": "https://xyz/hardcoded_url",
                },
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )

        self.assertEqual(Storage.__init__.call_args_list, [])
        self.assertEqual(File.__init__.call_args_list, [])
        self.assertEqual(File.upload.call_args_list, [])
        self.assertEqual(File.url.call_args_list, [])
