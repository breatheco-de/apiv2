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
from .slack import (
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
)
from .eventbrite import (
    EVENTBRITE_PATH,
    EVENTBRITE_INSTANCES,
    apply_eventbrite_requests_post_mock,
    EVENTBRITE_EVENT,
    EVENTBRITE_ORDER,
    EVENTBRITE_ATTENDEE,
    EVENTBRITE_TICKET_CLASS,
    EVENTBRITE_EVENT_URL,
    EVENTBRITE_ORDER_URL,
    EVENTBRITE_ATTENDEE_URL,
    EVENTBRITE_TICKET_CLASS_URL,
)
from .old_breathecode import (
    OLD_BREATHECODE_PATH,
    OLD_BREATHECODE_INSTANCES,
    apply_old_breathecode_requests_request_mock,
    OLD_BREATHECODE_ADMIN,
    OLD_BREATHECODE_ADMIN_URL,
    CONTACT_AUTOMATIONS,
    CONTACT_AUTOMATIONS_URL,
)
