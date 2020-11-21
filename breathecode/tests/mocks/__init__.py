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
