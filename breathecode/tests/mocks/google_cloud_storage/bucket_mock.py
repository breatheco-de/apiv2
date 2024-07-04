class BucketMock:
    name = None
    bucket = None
    files = {}

    def __init__(self, name):
        self.name = name

    def get_blob(self, blob_name):
        return self.files.get(blob_name)

    def blob(self, blob_name):
        from google.cloud.storage import Blob

        self.files[blob_name] = Blob(blob_name, self)
        return self.files[blob_name]

    def delete(self):
        return None
