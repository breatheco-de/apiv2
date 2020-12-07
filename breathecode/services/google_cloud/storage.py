import logging
from google.cloud import storage
from .credentials import resolve_credentials
from .file import File

logger = logging.getLogger(__name__)


class Storage:
    """Google Cloud Storage"""
    client = None

    def __init__(self):
        resolve_credentials()
        self.client = storage.Client()

    def file(self, bucket_name: str, file_name: str):
        """Get File object

        Args:
            bucket_name (str): Name of bucket in Google Cloud Storage
            file_name (str): Name of blob in Google Cloud Bucket

        Returns:
            File: File object
        """
        bucket = self.client.bucket(bucket_name)
        return File(bucket, file_name)
