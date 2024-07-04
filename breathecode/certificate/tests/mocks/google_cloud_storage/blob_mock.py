class BlobMock:
    public_url = None
    name = None
    content = None
    bucket = None

    def __init__(self, name, bucket):
        self.name = name
        self.bucket = bucket

    def upload_from_string(self, data):
        self.content = data
        return None

    def make_public(self):
        self.public_url = f"https://storage.cloud.google.com/{self.bucket.name}/{self.name}"

    def delete(self):
        return None

    def delete_blob(self):
        return None
