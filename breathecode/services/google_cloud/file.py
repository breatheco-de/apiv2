import requests, logging
# from google.cloud import storage
from google.cloud.storage import Bucket

logger = logging.getLogger(__name__)


class File:
    """Google Cloud Storage"""
    bucket = None
    blob = None
    file_name = None
    
    def __init__(self, bucket, file_name: str):
        self.file_name = file_name
        self.bucket = bucket
        self.blob = bucket.get_blob(file_name)

    def delete(self):
        """Delete Blob from Bucker"""
        if self.blob:
            self.blob.delete()

    def upload(self, content: str, public: False):
        """Delete Blob from Bucker"""
        self.blob = self.bucket.blob(self.file_name)
        self.blob.upload_from_string(content)

        if public:
            self.blob.make_public()

    def url(self) -> str:
        """Delete Blob from Bucker"""
        # TODO Private url
        return self.blob.public_url
