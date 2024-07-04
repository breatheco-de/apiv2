"""
Legacy breathecode API Mocks
"""

from unittest.mock import Mock
from .requests_mock import get_mock

LEGACY_API_PATH = {
    "get": "requests.get",
}

LEGACY_API_INSTANCES = {"get": Mock(side_effect=get_mock)}


def apply_screenshotmachine_requests_get_mock():
    """Apply Storage Blob Mock"""
    return LEGACY_API_INSTANCES["get"]
