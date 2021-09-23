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
    def test_academy_schedule__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:academy_schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_academy_schedule__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_schedule')
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

    def test_academy_schedule__without_specialty_mode(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_academy_schedule(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_schedule')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
            'syllabus': model.specialty_mode.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Syllabus id in querystring
    """

    def test_academy_schedule__syllabus_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_schedule') + '?syllabus_id=9999'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__syllabus_id_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_schedule') + '?syllabus_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
            'syllabus': model.specialty_mode.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Syllabus slug in querystring
    """

    def test_academy_schedule__syllabus_slug_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     specialty_mode=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__syllabus_slug_in_querystring(self):
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
        url = reverse_lazy('admissions:academy_schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'slug': model.specialty_mode.slug,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
            'syllabus': model.specialty_mode.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Delete
    """

    def test_certificate_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True)

        for field in many_fields:
            certificate_kwargs = {
                'logo':
                choice(['http://exampledot.com', 'http://exampledotdot.com', 'http://exampledotdotdot.com']),
                'week_hours':
                randint(0, 999999999),
                'schedule_type':
                choice(['PAR-TIME', 'FULL-TIME']),
            }
            model = self.generate_models(authenticate=True,
                                         profile_academy=True,
                                         capability='crud_certificate',
                                         role='potato',
                                         certificate_kwargs=certificate_kwargs,
                                         academy_specialty_mode=True,
                                         specialty_mode=True,
                                         models=base)
            url = (reverse_lazy('admissions:academy_schedule') + f'?{field}=' +
                   str(getattr(model['specialty_mode'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_certificate_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:academy_schedule')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_certificate_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Missing parameters in the querystring', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_certificate_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True)

        for field in many_fields:
            certificate_kwargs = {
                'logo':
                choice(['http://exampledot.com', 'http://exampledotdot.com', 'http://exampledotdotdot.com']),
                'week_hours':
                randint(0, 999999999),
                'schedule_type':
                choice(['PAR-TIME', 'FULL-TIME']),
            }
            model1 = self.generate_models(authenticate=True,
                                          profile_academy=True,
                                          capability='crud_certificate',
                                          role='potato',
                                          certificate_kwargs=certificate_kwargs,
                                          academy_specialty_mode=True,
                                          specialty_mode=True,
                                          models=base)

            model2 = self.generate_models(profile_academy=True,
                                          capability='crud_certificate',
                                          role='potato',
                                          certificate_kwargs=certificate_kwargs,
                                          academy_specialty_mode=True,
                                          specialty_mode=True,
                                          models=base)

            url = (reverse_lazy('admissions:academy_schedule') + f'?{field}=' +
                   str(getattr(model1['specialty_mode'], field)) + ',' +
                   str(getattr(model2['specialty_mode'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_specialty_mode_dict(), [])
