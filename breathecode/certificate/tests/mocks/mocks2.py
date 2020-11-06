"""
Collections of mocks used to login in authorize microservice
"""
from unittest.mock import Mock, MagicMock


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
