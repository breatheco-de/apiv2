import logging
import google.cloud.storage as storage
import breathecode.services.google_cloud.credentials as credentials
from .file import File

logger = logging.getLogger(__name__)

__all__ = ['Storage']


class Storage:
    """Google Cloud Storage"""
    client: storage.Client

    def __init__(self) -> None:
        # from google.cloud.storage import Client
        credentials.resolve_credentials()
        self.client = storage.Client()

    def file(self, bucket_name: str, file_name: str) -> File:
        """Get File object

        Args:
            bucket_name (str): Name of bucket in Google Cloud Storage
            file_name (str): Name of blob in Google Cloud Bucket

        Returns:
            File: File object
        """
        bucket = self.client.bucket(bucket_name)
        return File(bucket, file_name)
