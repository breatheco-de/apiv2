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


def get_serializer(syllabus_version, syllabus):
    return {
        'json': syllabus_version.json,
        'created_at': datetime_to_iso_format(syllabus_version.created_at),
        'updated_at': datetime_to_iso_format(syllabus_version.updated_at),
        'name': syllabus.name,
        'slug': syllabus.slug,
        'academy_owner': {
            'id': syllabus.academy_owner.id,
            'name': syllabus.academy_owner.name,
            'slug': syllabus.academy_owner.slug,
            'white_labeled': syllabus.academy_owner.white_labeled,
            'icon_url': syllabus.academy_owner.icon_url,
        },
        'syllabus': syllabus.id,
        'version': syllabus_version.version,
        'duration_in_days': syllabus.duration_in_days,
        'duration_in_hours': syllabus.duration_in_hours,
        'github_url': syllabus.github_url,
        'logo': syllabus.logo,
        'private': syllabus.private,
        'status': syllabus_version.status,
        'main_technologies': syllabus.main_technologies,
        'change_log_details': syllabus_version.change_log_details,
        'week_hours': syllabus.week_hours,
    }


class SyllabusVersionTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_syllabus_version_version_without_auth(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:all_syllabus_version')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_syllabus_version_version_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:all_syllabus_version')
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

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_syllabus_slug_version(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:all_syllabus_version')
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model['syllabus_version'], model['syllabus'])]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
        }])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_syllabus_slug_version_with_filters(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny', 'is_documentation': True}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_syllabus',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_kwargs=syllabus_kwargs)
        base_url = reverse_lazy('admissions:all_syllabus_version')
        url = f'{base_url}?is_documentation=True'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model['syllabus_version'], model['syllabus'])]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
        self.assertEqual(self.all_syllabus_version_dict(), [{
            **self.model_to_dict(model, 'syllabus_version')
        }])
