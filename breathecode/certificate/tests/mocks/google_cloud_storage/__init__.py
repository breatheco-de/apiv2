"""
Google Cloud Storage Mocks
"""
from unittest.mock import Mock
from .blob_mock import BlobMock
from .bucket_mock import BucketMock
from .client_mock import ClientMock

GOOGLE_CLOUD_PATH = {
    'client': 'google.cloud.storage.Client',
    'bucket': 'google.cloud.storage.Bucket',
    'blob': 'google.cloud.storage.Blob'
}

google_cloud_instances = {
    'client': None,
    'bucket': None,
    'blob': None
}

def apply_google_cloud_blob_mock():
    """Apply Storage Blob Mock"""
    mock = BlobMock
    google_cloud_instances['blob'] = mock
    return Mock(side_effect=mock)

def apply_google_cloud_bucket_mock():
    """Apply Storage Bucket Mock"""
    mock = BucketMock
    google_cloud_instances['bucket'] = mock
    return Mock(side_effect=mock)

def apply_google_cloud_client_mock():
    """Apply Storage Client Mock"""
    mock = ClientMock
    google_cloud_instances['client'] = mock
    return Mock(side_effect=mock)
