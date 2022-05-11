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
    def test_academy_id_syllabus_id_version_version_without_auth(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_id_syllabus_id_version_version',
                           kwargs={
                               'academy_id': 1,
                               'syllabus_id': 1,
                               'version': 1
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_syllabus_id_version_version_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_id_syllabus_id_version_version',
                           kwargs={
                               'academy_id': 1,
                               'syllabus_id': 1,
                               'version': 1
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
        self.assertEqual(self.all_syllabus_schedule_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_id_syllabus_id_version_version_without_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato')
        url = reverse_lazy('admissions:academy_id_syllabus_id_version_version',
                           kwargs={
                               'academy_id': 1,
                               'syllabus_id': 1,
                               'version': 1
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'syllabus-version-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_syllabus_version_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_id_syllabus_id_version_version(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True)
        url = reverse_lazy('admissions:academy_id_syllabus_id_version_version',
                           kwargs={
                               'academy_id': 1,
                               'syllabus_id': 1,
                               'version': model.syllabus_version.version
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'json': model['syllabus_version'].json,
            'created_at': datetime_to_iso_format(model['syllabus_version'].created_at),
            'updated_at': datetime_to_iso_format(model['syllabus_version'].updated_at),
            'name': model.syllabus.name,
            'slug': model['syllabus'].slug,
            'syllabus': 1,
            'academy_owner': {
                'id': model['syllabus'].academy_owner.id,
                'name': model['syllabus'].academy_owner.name,
                'slug': model['syllabus'].academy_owner.slug,
            },
            'version': model['syllabus_version'].version,
            'duration_in_days': model.syllabus.duration_in_days,
            'duration_in_hours': model.syllabus.duration_in_hours,
            'github_url': model.syllabus.github_url,
            'logo': model.syllabus.logo,
            'change_log_details': model.syllabus_version.change_log_details,
            'status': model.syllabus_version.status,
            'private': model.syllabus.private,
            'week_hours': model.syllabus.week_hours,
            'main_technologies': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
