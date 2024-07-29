"""
Google Cloud Storage Mocks
"""

from unittest.mock import Mock
from .blob_mock import BlobMock
from .bucket_mock import BucketMock
from .client_mock import ClientMock

GOOGLE_CLOUD_PATH = {
    "client": "google.cloud.storage.Client",
    "bucket": "google.cloud.storage.Bucket",
    "blob": "google.cloud.storage.Blob",
}

GOOGLE_CLOUD_INSTANCES = {
    "client": Mock(side_effect=ClientMock),
    "bucket": Mock(side_effect=BucketMock),
    "blob": Mock(side_effect=BlobMock),
}


def apply_google_cloud_blob_mock():
    """Apply Storage Blob Mock"""
    return GOOGLE_CLOUD_INSTANCES["blob"]


def apply_google_cloud_bucket_mock():
    """Apply Storage Bucket Mock"""
    return GOOGLE_CLOUD_INSTANCES["bucket"]


def apply_google_cloud_client_mock():
    """Apply Storage Client Mock"""
    return GOOGLE_CLOUD_INSTANCES["client"]
