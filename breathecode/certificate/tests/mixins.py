"""
Collections of mixins used to login in authorize microservice
"""
import os
import base64
import urllib
from unittest.mock import patch, mock_open, create_autospec
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient
from django.test import TransactionTestCase
from mixer.backend.django import mixer
from pprint import pprint
from .mocks import CertificateBreathecodeMock, GoogleCloudMock, FakeGoogleCloudStorageClientMock
from google.cloud import storage


class DevelopmentEnvironment():
    def __init__(self):
        os.environ['ENV'] = 'development'


class CertificateTestCase(TransactionTestCase, DevelopmentEnvironment):
# class CertificateTestCase(APITestCase, DevelopmentEnvironment):
    """CertificateTestCase with Slack methods"""
    token = '9e76a2ab3bd55454c384e0a5cdb5298d17285949'
    user = None
    cohort = None
    cohort_user = None

    @patch('google.cloud.storage',
        GoogleCloudMock.apply_storage_mock())
    @patch('breathecode.activity.utils.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    @patch('breathecode.admissions.actions.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    @patch('breathecode.certificate.actions.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    @patch('__main__.open', mock_open())
    # @patch('google.cloud.storage.client.Client', autospec=True)
    # @patch('google.cloud.storage.client.Client' MagicMock())
    def setUp(self):
        storage_client = create_autospec(storage.Client)
        mock_bucket = create_autospec(storage.Bucket)
        mock_blob = create_autospec(storage.Blob)
        mock_bucket.return_value = mock_blob
        storage_client.get_bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob
        mock_blob.public_url.return_value = "file_content"

        print(mock_blob.public_url)


        # x.return_value = FakeGoogleCloudStorageClientMock
        open = mock_open()

        certificate = mixer.blend('admissions.Certificate')
        # certificate.token = self.token
        certificate.save()

        # user as certificate
        user_specialty = mixer.blend('certificate.UserSpecialty')
        user_specialty.token = self.token
        user_specialty.save()

        user = mixer.blend('auth.User')
        user.save()
        self.user = user

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate.id
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user.id
        cohort_user.cohort = cohort.id
        cohort_user.save()
        self.cohort_user = cohort_user
