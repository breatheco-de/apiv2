"""
Google Cloud Storage Mocks
"""
from unittest.mock import Mock
from .logger_mock import post_mock

LOGGING_PATH = {
    'logger': 'logging.Logger',
}

LOGGING_INSTANCES = {
    'logger': Mock(side_effect=post_mock)
}

def apply_mailgun_requests_post_mock():
    """Apply Storage Blob Mock"""
    return LOGGING_INSTANCES['logger']
