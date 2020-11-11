"""
Mocks
"""
from .google_cloud_storage import (
    GOOGLE_CLOUD_PATH,
    GOOGLE_CLOUD_INSTANCES,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from .screenshotmachine import (
    SCREENSHOTMACHINE_PATH,
    SCREENSHOTMACHINE_INSTANCES,
    apply_requests_get_mock,
)
from .credentials import (
    CREDENTIALS_PATH,
    CREDENTIALS_INSTANCES,
    apply_resolve_credentials_mock,
)
from .actions import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_certificate_screenshot_mock,
    apply_generate_certificate_mock,
    apply_remove_certificate_screenshot_mock,
)
