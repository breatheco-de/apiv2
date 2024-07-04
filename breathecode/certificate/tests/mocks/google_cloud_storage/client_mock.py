from .bucket_mock import BucketMock


class ClientMock:

    def bucket(self, bucket_name):
        return BucketMock(bucket_name)
