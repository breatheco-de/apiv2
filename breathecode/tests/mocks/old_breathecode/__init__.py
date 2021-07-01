"""
Google Cloud Storage Mocks
"""
from unittest.mock import Mock
from .requests_mock import request_mock
from .constants import (OLD_BREATHECODE_ADMIN, OLD_BREATHECODE_ADMIN_URL,
                        CONTACT_AUTOMATIONS, CONTACT_AUTOMATIONS_URL)

OLD_BREATHECODE_PATH = {
    'request': 'requests.request',
}

OLD_BREATHECODE_INSTANCES = {'request': Mock(side_effect=request_mock)}


def apply_old_breathecode_requests_request_mock():
    """Apply Storage Blob Mock"""
    return OLD_BREATHECODE_INSTANCES['request']
