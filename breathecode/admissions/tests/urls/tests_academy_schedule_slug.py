"""
Test /certificate
"""
from random import choice, randint
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 Auth
    """
    def test_academy_schedule_slug__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:academy_schedule_slug',
                           kwargs={'certificate_slug': 'they-killed-kenny'})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_academy_schedule_slug__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_schedule_slug',
                           kwargs={'certificate_slug': 'they-killed-kenny'})
        self.generate_models(authenticate=True)
        response = self.client.put(url)
        json = response.json()
        expected = {
            'status_code': 403,
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1"
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_academy_schedule_slug__not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_slug',
                           kwargs={'certificate_slug': 'they-killed-kenny'})
        response = self.client.put(url)
        json = response.json()
        expected = {
            'detail': 'specialty-mode-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_academy_schedule_slug__bad_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_slug',
                           kwargs={'certificate_slug': model.specialty_mode.slug})
        data = {
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'description': 'Oh my god!',
            'syllabus': 2,
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'syllabus-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        }])

    def test_academy_schedule_slug(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_slug',
                           kwargs={'certificate_slug': model.specialty_mode.slug})
        data = {'slug': 'they-killed-kenny', 'name': 'They killed kenny', 'description': 'Oh my god!'}
        response = self.client.put(url, data)
        json = response.json()

        self.assertDatetime(json['updated_at'])
        del json['updated_at']

        expected = {
            'created_at': self.datetime_to_iso(model.specialty_mode.created_at),
            'id': model.specialty_mode.id,
            'schedule_type': model.specialty_mode.schedule_type,
            'syllabus': model.specialty_mode.syllabus,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
            **data,
        }])
