"""
Test /certificate
"""
from unittest.mock import patch
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_slug_academy_id_syllabus_version_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': '1'
            })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_certificate_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_certificate_slug_academy_id_syllabus_version_without_capability(
            self):
        """Test /certificate without auth"""
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': '1'
            })
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'status_code':
            403,
            'detail':
            'You (user: 1) don\'t have this capability: read_syllabus '
            'for academy 1'
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_certificate_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_certificate_slug_academy_id_syllabus_version_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': '1'
            })
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato')
        response = self.client.get(url)
        json = response.json()
        expected = {'status_code': 404, 'detail': 'Certificate slug not found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_without_syllabus(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     certificate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato')
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': model['certificate'].slug,
                'academy_id': 1,
                'version': '1'
            })
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Syllabus not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_with_bad_version(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     certificate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': model['certificate'].slug,
                'academy_id': 1,
                'version': '1'
            })
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Syllabus not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': model['syllabus'].json,
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     certificate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': model['certificate'].slug,
                'academy_id': 1,
                'version': model['syllabus'].version
            })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'certificate': model['certificate'].slug,
            'json': model['syllabus'].json,
            'updated_at': datetime_to_iso_format(model['syllabus'].updated_at),
            'version': model['syllabus'].version,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': model['syllabus'].json,
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_auth(
            self):
        """Test /certificate without auth"""
        model = self.generate_models()
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': 1
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': 401
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_capability(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': 1
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail':
            "You (user: 1) don't have this capability: crud_syllabus "
            "for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_syllabus(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato')
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': 1
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'Syllabus version not found for this academy',
            'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_bad_version(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': 1
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'Syllabus version not found for this academy',
            'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': model['syllabus'].json,
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_bad_slug(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': 'they-killed-kenny',
                'academy_id': 1,
                'version': model['syllabus'].version
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'Syllabus version not found for this academy',
            'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': model['syllabus'].json,
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_certificate_slug_academy_id_syllabus_version__put__without_time_slot(self):
    #     """Test /certificate without auth"""
    #     model = self.generate_models(authenticate=True, profile_academy=True,
    #         capability='crud_syllabus', role='potato', syllabus=True,
    #         certificate=True)
    #     url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
    #         kwargs={'certificate_slug': model['certificate'].slug, 'academy_id': 1,
    #         'version': model['syllabus'].version})
    #     data = {}
    #     response = self.client.put(url, data)
    #     json = response.json()
    #     expected = {
    #         'detail': 'certificate-not-have-time-slots',
    #         'status_code': 400,
    #     }

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(self.all_syllabus_dict(), [{
    #         'academy_owner_id': model['syllabus'].academy_owner_id,
    #         'certificate_id': model['syllabus'].certificate_id,
    #         'github_url': model['syllabus'].github_url,
    #         'id': model['syllabus'].id,
    #         'json': model['syllabus'].json,
    #         'private': model['syllabus'].private,
    #         'version': model['syllabus'].version
    #     }])
    #     self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_json_field(
            self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     certificate=True,
                                     certificate_time_slot=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': model['certificate'].slug,
                'academy_id': 1,
                'version': model['syllabus'].version
            })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'json': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': model['syllabus'].json,
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     certificate=True,
                                     certificate_time_slot=True)
        url = reverse_lazy(
            'admissions:certificate_slug_academy_id_syllabus_version',
            kwargs={
                'certificate_slug': model['certificate'].slug,
                'academy_id': 1,
                'version': model['syllabus'].version
            })
        data = {'json': {'ova': 'thus spoke kishibe rohan'}}
        response = self.client.put(url, data, format='json')
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['updated_at']

        expected = {
            'academy_owner': model['syllabus'].academy_owner_id,
            'certificate': model['syllabus'].certificate_id,
            'created_at': self.datetime_to_iso(model['syllabus'].created_at),
            'github_url': model['syllabus'].github_url,
            'id': model['syllabus'].id,
            'json': data['json'],
            'private': model['syllabus'].private,
            'version': model['syllabus'].version
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_dict(), [{
                'academy_owner_id': model['syllabus'].academy_owner_id,
                'certificate_id': model['syllabus'].certificate_id,
                'github_url': model['syllabus'].github_url,
                'id': model['syllabus'].id,
                'json': data['json'],
                'private': model['syllabus'].private,
                'version': model['syllabus'].version
            }])
