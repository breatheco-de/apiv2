"""
Mocks
"""

# flake8: noqa: F401

from .actions import (
    ACTIONS_INSTANCES,
    ACTIONS_PATH,
    apply_certificate_screenshot_mock,
    apply_generate_certificate_mock,
    apply_remove_certificate_screenshot_mock,
)
from .credentials import CREDENTIALS_INSTANCES, CREDENTIALS_PATH, apply_resolve_credentials_mock
from .google_cloud_storage import (
    GOOGLE_CLOUD_INSTANCES,
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)
from .screenshotmachine import (
    SCREENSHOTMACHINE_INSTANCES,
    SCREENSHOTMACHINE_PATH,
    apply_screenshotmachine_requests_get_mock,
)
