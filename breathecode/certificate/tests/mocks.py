"""
Collections of mocks used to login in authorize microservice
"""
from unittest.mock import Mock, MagicMock


def requests_mock(routes: dict, method='get'):
    """Arequests mock"""
    if method == 'get':
        def side_effect (url, headers=None):
            return routes.get(url, f'unhandled request {url}')
    elif method == 'post':
        def side_effect (url, data=None, headers=None):
            return routes.get(url, f'unhandled request {url}')
    else:
        raise Exception(f'{method} are not implemented too')
    return Mock(side_effect=side_effect)


class FakeResponse():
    """Simutate Response to be used by mocks"""
    status_code = 200
    data = {}

    def __init__(self, status_code, data):
        self.data = data
        self.status_code = status_code

    def json(self):
        """Convert Response to JSON"""
        return self.data

class FakeHtmlResponse():
    """Simutate Response to be used by mocks"""
    status_code = 200
    content = ''

    def __init__(self, status_code, content):
        self.content = content
        self.status_code = status_code


class FakeGoogleCloudBlobMock():
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
        self.public_url = f'https://storage.cloud.google.com/{self.bucket.name}/{self.name}'

    def delete(self):
        return None


class FakeGoogleCloudBucketMock():
    name = None
    bucket = None
    files = {}

    def __init__(self, name):
        self.name = name

    def get_blob(self, blob_name):
        file = self.files.get(blob_name)

        if not file:
            file = FakeGoogleCloudBlobMock(blob_name, self)
            self.files[blob_name] = file

        return file

    def blob(self, blob_name):
        self.files[blob_name] = FakeGoogleCloudBlobMock(blob_name, self)
        return self.files[blob_name]

    def delete(self):
        return None


class FakeGoogleCloudStorageClientMock():
    def bucket(self, bucket_name):
        return FakeGoogleCloudBucketMock(bucket_name)

fake_google_cloud_bucket = MagicMock(
    bucket=lambda bucket_name: FakeGoogleCloudBucketMock(bucket_name),
    delete=lambda: None
)
fake_google_cloud_storage_client = MagicMock(bucket=lambda bucket_name: FakeGoogleCloudBucketMock(bucket_name))


class GoogleCloudStorageMock():
    @staticmethod
    def get_bucket_object():
        def side_effect():
            return None
        return Mock(side_effect=side_effect)


class GoogleCloudMock():
    """Github requests mock"""
    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"

    @staticmethod
    def preview():
        filename = 'preview.html'
        with open(filename, 'r') as file:
            return file.read()
        return f'File not exist `{filename}`'

    @staticmethod
    def google_cloud_storage_client():
        return FakeGoogleCloudStorageClientMock()

    @staticmethod
    def apply_storage_mock():
        """Apply get requests mock"""
        return Mock(side_effect=GoogleCloudMock.google_cloud_storage_client())


class BreathecodeMock():
    """Github requests mock"""
    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"

    @staticmethod
    def resolve_google_credentials():
        return None

    @staticmethod
    def apply_resolve_google_credentials_mock():
        """Apply get requests mock"""
        return Mock(side_effect=BreathecodeMock.resolve_google_credentials())


class CertificateBreathecodeMock(BreathecodeMock):
    """Github requests mock"""
    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"

    @staticmethod
    def preview():
        filename = 'preview.html'
        with open(filename, 'r') as file:
            return FakeHtmlResponse(200, file.read())
        return FakeHtmlResponse(200, f'File not exist `{filename}`')

    @staticmethod
    def apply_storage_mock():
        """Apply get requests mock"""
        preview_url = (
            'https://certificate.breatheco.de/preview/'
            '9e76a2ab3bd55454c384e0a5cdb5298d17285949'
        )
        routes =  {
            f'{preview_url}': CertificateBreathecodeMock.preview()
        }
        return requests_mock(routes, method='post')
