from .blob_mock import BlobMock

class BucketMock():
    name = None
    bucket = None
    files = {}

    def __init__(self, name):
        self.name = name

    def get_blob(self, blob_name):
        file = self.files.get(blob_name)

        if not file:
            file = BlobMock(blob_name, self)
            self.files[blob_name] = file

        return file

    def blob(self, blob_name):
        self.files[blob_name] = BlobMock(blob_name, self)
        return self.files[blob_name]

    def delete(self):
        return None
