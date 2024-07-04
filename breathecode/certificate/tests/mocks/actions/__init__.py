"""
Google Cloud Storage Mocks
"""

from unittest.mock import Mock
from .certificate_screenshot_mock import certificate_screenshot_mock
from .generate_certificate_mock import generate_certificate_mock
from .remove_certificate_screenshot_mock import remove_certificate_screenshot_mock

ACTIONS_PATH = {
    "certificate_screenshot": "breathecode.certificate.actions.certificate_screenshot",
    "generate_certificate": "breathecode.certificate.actions.generate_certificate",
    "remove_certificate_screenshot": "breathecode.certificate.actions.remove_certificate_screenshot",
}

ACTIONS_INSTANCES = {
    "certificate_screenshot": Mock(side_effect=certificate_screenshot_mock),
    "generate_certificate": Mock(side_effect=generate_certificate_mock),
    "remove_certificate_screenshot": Mock(side_effect=remove_certificate_screenshot_mock),
}


def apply_certificate_screenshot_mock():
    """Apply certificate_screenshot Mock"""
    return ACTIONS_INSTANCES["certificate_screenshot"]


def apply_generate_certificate_mock():
    """Apply generate_certificate Mock"""
    return ACTIONS_INSTANCES["generate_certificate"]


def apply_remove_certificate_screenshot_mock():
    """Apply remove_certificate_screenshot Mock"""
    return ACTIONS_INSTANCES["remove_certificate_screenshot"]
