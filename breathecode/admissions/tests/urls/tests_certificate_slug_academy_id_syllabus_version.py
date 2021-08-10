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
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_slug_academy_id_syllabus_version_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
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
        self.assertEqual(self.all_specialty_mode_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_certificate_slug_academy_id_syllabus_version_without_capability(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': 'they-killed-kenny',
                               'academy_id': 1,
                               'version': '1'
                           })
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'status_code': 403,
            'detail': 'You (user: 1) don\'t have this capability: read_syllabus '
            'for academy 1'
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_specialty_mode_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_certificate_slug_academy_id_syllabus_version_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': 'they-killed-kenny',
                               'academy_id': 1,
                               'version': '1'
                           })
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     specialty_mode=True,
                                     role='potato')
        response = self.client.get(url)
        json = response.json()
        expected = {'status_code': 404, 'detail': 'specialty-mode-not-found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_without_syllabus(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato')
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model['specialty_mode'].slug,
                               'academy_id': 1,
                               'version': '1'
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'syllabus-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_syllabus_version_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_with_bad_version(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model['specialty_mode'].slug,
                               'academy_id': 1,
                               'version': '1'
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'syllabus-version-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model['specialty_mode'].slug,
                               'academy_id': 1,
                               'version': model['syllabus_version'].version
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'json': model['syllabus_version'].json,
            'created_at': datetime_to_iso_format(model['syllabus_version'].created_at),
            'updated_at': datetime_to_iso_format(model['syllabus_version'].updated_at),
            'syllabus': 1,
            'version': model['syllabus_version'].version,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_specialty_mode(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato')
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': 'they-killed-kenny',
                               'academy_id': 1,
                               'version': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'specialty-mode-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_syllabus_version_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_with_bad_version(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model.specialty_mode.slug,
                               'academy_id': 1,
                               'version': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'syllabus-version-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version__put__specialty_mode_without_syllabus(self):
        """Test /certificate without auth"""
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='crud_syllabus',
            role='potato',
            specialty_mode=True,
            #  syllabus=True,
            syllabus_version=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model.specialty_mode.slug,
                               'academy_id': 1,
                               'version': model['syllabus_version'].version
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'specialty-mode-without-syllabus', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_slug_academy_id_syllabus_version_put_without_json_field(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model['specialty_mode'].slug,
                               'academy_id': 1,
                               'version': model['syllabus_version'].version
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'json': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
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
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True)
        url = reverse_lazy('admissions:certificate_slug_academy_id_syllabus_version',
                           kwargs={
                               'certificate_slug': model['specialty_mode'].slug,
                               'academy_id': 1,
                               'version': model['syllabus_version'].version
                           })
        data = {'json': {'ova': 'thus spoke kishibe rohan'}}
        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {
            'json': data['json'],
            'syllabus': model.syllabus.id,
            'version': model.syllabus_version.version,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version'),
            'json': {
                'ova': 'thus spoke kishibe rohan',
            },
        }])
