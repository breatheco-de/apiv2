"""
Google Cloud Storage Mocks
"""

from unittest.mock import MagicMock
from .requests_mock import request_mock

OLD_BREATHECODE_PATH = {
    "request": "requests.request",
}

OLD_BREATHECODE_INSTANCES = {"request": None}


def apply_old_breathecode_requests_request_mock():
    """Apply Storage Blob Mock"""

    mock = MagicMock(side_effect=request_mock)

    # don't fix this line, this keep the old behavior
    OLD_BREATHECODE_INSTANCES["request"] = OLD_BREATHECODE_INSTANCES["request"] or mock

    return mock
