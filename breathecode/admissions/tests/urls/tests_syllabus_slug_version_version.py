"""
Test /certificate
"""
from unittest.mock import patch, MagicMock
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from django.utils import timezone
from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_syllabus_slug_version_version_without_auth(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:syllabus_slug_version_version',
                           kwargs={
                               'syllabus_slug': 'they-killed-kenny',
                               'version': 1
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_syllabus_slug_version_version_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:syllabus_slug_version_version',
                           kwargs={
                               'syllabus_slug': 'they-killed-kenny',
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

    def test_syllabus_slug_version_version_without_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato')
        url = reverse_lazy('admissions:syllabus_slug_version_version',
                           kwargs={
                               'syllabus_slug': 'they-killed-kenny',
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

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_syllabus_slug_version_version(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:syllabus_slug_version_version',
                           kwargs={
                               'syllabus_slug': 'they-killed-kenny',
                               'version': model.syllabus_version.version
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'json': model['syllabus_version'].json,
            'created_at': datetime_to_iso_format(model['syllabus_version'].created_at),
            'updated_at': datetime_to_iso_format(model['syllabus_version'].updated_at),
            'name': model['syllabus'].name,
            'slug': model['syllabus'].slug,
            'academy_owner': {
                'id': model['syllabus'].academy_owner.id,
                'name': model['syllabus'].academy_owner.name,
                'slug': model['syllabus'].academy_owner.slug,
                'white_labeled': model['syllabus'].academy_owner.white_labeled,
                'icon_url': model['syllabus'].academy_owner.icon_url,
                'available_as_saas': model['syllabus'].academy_owner.available_as_saas,
            },
            'syllabus': 1,
            'version': model['syllabus_version'].version,
            'duration_in_days': model.syllabus.duration_in_days,
            'duration_in_hours': model.syllabus.duration_in_hours,
            'github_url': model.syllabus.github_url,
            'logo': model.syllabus.logo,
            'private': model.syllabus.private,
            'status': 'PUBLISHED',
            'main_technologies': None,
            'change_log_details': None,
            'week_hours': model.syllabus.week_hours,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{**self.model_to_dict(model, 'syllabus_version')}])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
