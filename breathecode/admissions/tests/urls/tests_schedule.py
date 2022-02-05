"""
Test /certificate
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice, randint
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_specialty_mode(), 0)

    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True, syllabus=True, specialty_mode=True)
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['specialty_mode'].id,
            'name': model['specialty_mode'].name,
            'description': model['specialty_mode'].description,
            'syllabus': model['specialty_mode'].syllabus.id,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        }])

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
        url = reverse_lazy('admissions:schedule') + '?syllabus_id=9999'
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
        url = reverse_lazy('admissions:schedule') + '?syllabus_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
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
        url = reverse_lazy('admissions:schedule') + '?syllabus_slug=they-killed-kenny'
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
        url = reverse_lazy('admissions:schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.specialty_mode.id,
            'name': model.specialty_mode.name,
            'description': model.specialty_mode.description,
            'syllabus': model.specialty_mode.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Pagination
    """

    def test_certificate_with_data_without_pagination_get_just_100(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [
            self.generate_models(specialty_mode=True, syllabus=True, models=base) for _ in range(0, 105)
        ]
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['specialty_mode'].id,
            'name': model['specialty_mode'].name,
            'description': model['specialty_mode'].description,
            'syllabus': model['specialty_mode'].syllabus.id,
        } for model in models if model['specialty_mode'].id <= 100])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_first_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, syllabus=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:schedule') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count':
                10,
                'first':
                None,
                'last':
                'http://testserver/v1/admissions/schedule?limit=5&offset=5',
                'next':
                'http://testserver/v1/admissions/schedule?limit=5&offset=5',
                'previous':
                None,
                'results': [{
                    'id': model['specialty_mode'].id,
                    'name': model['specialty_mode'].name,
                    'description': model['specialty_mode'].description,
                    'syllabus': model['specialty_mode'].syllabus.id,
                } for model in models if model['specialty_mode'].id <= 5]
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, syllabus=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:schedule') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count':
                10,
                'first':
                'http://testserver/v1/admissions/schedule?limit=5',
                'last':
                None,
                'next':
                None,
                'previous':
                'http://testserver/v1/admissions/schedule?limit=5',
                'results': [{
                    'id': model['specialty_mode'].id,
                    'name': model['specialty_mode'].name,
                    'description': model['specialty_mode'].description,
                    'syllabus': model['specialty_mode'].syllabus.id,
                } for model in models if model['specialty_mode'].id > 5],
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_after_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:schedule') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count': 10,
                'first': 'http://testserver/v1/admissions/schedule?limit=5',
                'last': None,
                'next': None,
                'previous': 'http://testserver/v1/admissions/schedule?limit=5&offset=5',
                'results': [],
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])
