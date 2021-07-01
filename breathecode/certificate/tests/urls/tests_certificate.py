"""
Test /certificate
"""
import re
from random import choice
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_certificate_test_case import CertificateTestCase


class CertificateTestSuite(CertificateTestCase):
    """Test '' """
    def test_delete_certificate_in_bulk_without_auth(self):
        url = reverse_lazy('certificate:certificate_academy') + '?id=1,2'
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_certificate_in_bulk_wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('certificate:certificate_academy') + '?id=1,2'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_certificate_in_bulk_without_capability(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, )
        url = reverse_lazy('certificate:certificate_academy') + '?id=1,2'
        response = self.client.delete(url)
        json = response.json()
        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: crud_certificate for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_with_two_ids(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(
            user=True,
            profile_academy=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'hitman3000'},
            models=base)

        model2 = self.generate_models(
            user=True,
            profile_academy=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'batman2000'},
            models=base)

        url = reverse_lazy('certificate:certificate_academy') + '?id=1,2'
        response = self.client.delete(url)

        if response.status_code != 204:
            print(response.json())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_user_invite_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_not_found(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(
            user=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'hitman3000'},
            models=base)

        model2 = self.generate_models(
            user=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'batman2000'},
            models=base)

        url = reverse_lazy('certificate:certificate_academy') + '?id=3,4'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {
            'detail': 'specialties_not_found',
            'status_code': 404
        })
        self.assertEqual(self.all_user_invite_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_without_passing_ids(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(
            user=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'hitman3000'},
            models=base)

        model2 = self.generate_models(
            user=True,
            user_specialty=True,
            user_specialty_kwargs={'token': 'batman2000'},
            models=base)

        url = reverse_lazy('certificate:certificate_academy')
        response = self.client.delete(url)

        if response.status_code != 204:
            print(response.json())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {
            'detail': 'missing_ids',
            'status_code': 404
        })
        self.assertEqual(self.all_user_invite_dict(), [])
