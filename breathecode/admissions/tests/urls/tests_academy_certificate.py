"""
Test /certificate
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 Auth
    """
    def test_academy_certificate__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:academy_certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_academy_certificate__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_certificate')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'status_code': 403,
            'detail': "You (user: 1) don't have this capability: read_certificate for academy 1"
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_academy_certificate__without_specialty_mode(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_certificate')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_academy_certificate(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_certificate')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Syllabus id in querystring
    """

    def test_academy_certificate__syllabus_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_certificate') + '?syllabus_id=9999'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_certificate__syllabus_id_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_certificate') + '?syllabus_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Syllabus slug in querystring
    """

    def test_academy_certificate__syllabus_slug_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_certificate') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_certificate__syllabus_slug_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)

        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_certificate') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])
