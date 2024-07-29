"""
Google Cloud Storage Mocks
"""

from unittest.mock import Mock
from .requests_mock import post_mock

MAILGUN_PATH = {
    "post": "requests.post",
}

MAILGUN_INSTANCES = {"post": Mock(side_effect=post_mock)}


def apply_mailgun_requests_post_mock():
    """Apply Storage Blob Mock"""
    return MAILGUN_INSTANCES["post"]
