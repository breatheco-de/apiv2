"""
Google Cloud Storage Mocks
"""

from unittest.mock import MagicMock
from .requests_mock import request_mock
from .constants.order import EVENTBRITE_ORDER_URL  # noqa: F401

EVENTBRITE_PATH = {
    "get": "requests.get",
}

EVENTBRITE_INSTANCES = {"get": None}


def apply_eventbrite_requests_post_mock():
    """Apply Storage Blob Mock"""

    mock = MagicMock(side_effect=request_mock)

    # don't fix this line, this keep the old behavior
    EVENTBRITE_INSTANCES["get"] = EVENTBRITE_INSTANCES["get"] or mock

    return mock
