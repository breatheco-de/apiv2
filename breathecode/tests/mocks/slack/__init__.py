"""Google Cloud Storage Mocks."""

from unittest.mock import Mock

from .requests_mock import request_mock

SLACK_PATH = {
    "request": "requests.request",
}

SLACK_INSTANCES = {"request": Mock(side_effect=request_mock)}


def apply_slack_requests_request_mock():
    """Apply Storage Blob Mock."""
    return SLACK_INSTANCES["request"]
