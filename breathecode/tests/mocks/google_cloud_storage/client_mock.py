class ClientMock:

    def bucket(self, bucket_name):
        from google.cloud.storage import Bucket

        return Bucket(bucket_name)
