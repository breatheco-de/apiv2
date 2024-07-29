import logging
from io import BufferedReader, BytesIO, StringIO, TextIOWrapper
from typing import Optional, overload

from circuitbreaker import circuit
from google.cloud.storage import Blob, Bucket

logger = logging.getLogger(__name__)

__all__ = ["File"]


class File:
    """Google Cloud Storage"""

    bucket: Bucket
    blob: Blob
    file_name: str

    def __init__(self, bucket: Bucket, file_name: str):
        self.file_name = file_name
        self.bucket = bucket
        self.blob = self._get_blob()

    @circuit
    def _get_blob(self) -> Blob:
        """Get Blob from Bucket"""
        return self.bucket.get_blob(self.file_name)

    @circuit
    def delete(self):
        """Delete Blob from Bucket"""
        if self.blob:
            self.blob.delete()

    @circuit
    def upload(self, content, public: bool = False, content_type: str = "text/plain") -> None:
        """Upload Blob from Bucket"""
        self.blob = self.bucket.blob(self.file_name)

        if content_type is None:
            content_type = "application/octet-stream"

        if isinstance(content, str) or isinstance(content, bytes):
            self.blob.upload_from_string(content, content_type=content_type)
        else:
            content.seek(0)
            self.blob.upload_from_file(content, content_type=content_type)

        if public:
            self.blob.make_public()

    @circuit
    def exists(self) -> bool:
        """Check if Blob exists in Bucket"""

        return self.bucket.blob(self.file_name).exists()

    @circuit
    def url(self) -> str:
        """Delete Blob from Bucket"""
        # TODO Private url
        return self.blob.public_url

    @overload
    def download(self, file: StringIO | TextIOWrapper) -> None: ...

    @overload
    def download(self, file: BytesIO | BufferedReader) -> None: ...

    @overload
    def download(self, file: None) -> bytes: ...

    @overload
    def download(self) -> bytes: ...

    @circuit
    def download(self, file: Optional[BytesIO | StringIO]) -> bytes | None:
        """Delete Blob from Bucket"""
        if self.blob and file:
            return self.blob.download_to_file(file)

        elif self.blob:
            return self.blob.download_as_string()

    @circuit
    def stream_download(self) -> str:
        """Delete Blob from Bucket"""

        class Echo:
            """An object that implements just the write method of the file-like
            interface.
            """

            def __init__(self):
                self.pieces = []

            def write(self, value):
                """Write the value by returning it, instead of storing in a buffer."""
                self.pieces.append(value.decode("latin1"))

            def all(self):
                return self.pieces

        streamer = Echo()
        blob = self.bucket.blob(self.file_name)
        blob.download_to_file(streamer)
        return streamer

    @circuit
    def rename(self, file_name: str) -> None:
        """Renames a blob."""

        blob = self.bucket.blob(self.file_name)
        self.bucket.rename_blob(blob, file_name)
