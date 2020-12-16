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
from .celery import (
    CELERY_PATH,
    CELERY_INSTANCES,
    apply_celery_shared_task_mock,
)
from .django_contrib import (
    DJANGO_CONTRIB_PATH,
    DJANGO_CONTRIB_INSTANCES,
    apply_django_contrib_messages_mock,
)
from .mailgun import (
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_requests_post_mock,
)
