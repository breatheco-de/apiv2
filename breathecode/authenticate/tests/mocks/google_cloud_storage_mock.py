"""
Collections of mocks used to login in authorize microservice
"""

from unittest.mock import Mock


class GoogleCloudStorageMock:

    @staticmethod
    def get_bucket_object():

        def side_effect():
            return None

        return Mock(side_effect=side_effect)
