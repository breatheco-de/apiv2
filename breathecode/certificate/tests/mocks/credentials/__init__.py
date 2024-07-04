"""
Google Cloud Storage Mocks
"""

from unittest.mock import Mock
from .resolve_credentials_mock import resolve_credentials_mock

CREDENTIALS_PATH = {
    "resolve_credentials": "breathecode.services.google_cloud.credentials.resolve_credentials",
}

CREDENTIALS_INSTANCES = {"resolve_credentials": Mock(side_effect=resolve_credentials_mock)}


def apply_resolve_credentials_mock():
    """Apply Resolve Credentials Mock"""
    return CREDENTIALS_INSTANCES["resolve_credentials"]
