"""
Google Cloud Storage Mocks
"""

from unittest.mock import Mock
from .requests_mock import get_mock

SCREENSHOTMACHINE_PATH = {
    "get": "requests.get",
}

SCREENSHOTMACHINE_INSTANCES = {"get": Mock(side_effect=get_mock)}


def apply_screenshotmachine_requests_get_mock():
    """Apply Storage Blob Mock"""
    return SCREENSHOTMACHINE_INSTANCES["get"]
