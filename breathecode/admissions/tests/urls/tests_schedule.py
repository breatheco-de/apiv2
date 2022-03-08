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
        self.bc.database.create(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_syllabus_schedule(), 0)

    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.bc.database.create(authenticate=True, syllabus=True, syllabus_schedule=True)
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['syllabus_schedule'].id,
            'name': model['syllabus_schedule'].name,
            'description': model['syllabus_schedule'].description,
            'syllabus': model['syllabus_schedule'].syllabus.id,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        }])

    """
    🔽🔽🔽 Syllabus id in querystring
    """

    def test_academy_schedule__syllabus_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
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
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?syllabus_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
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
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
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
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Pagination
    """

    def test_certificate_with_data_without_pagination_get_just_100(self):
        """Test /certificate without auth"""
        base = self.bc.database.create(authenticate=True)
        models = [
            self.bc.database.create(syllabus_schedule=True, syllabus=True, models=base)
            for _ in range(0, 105)
        ]
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['syllabus_schedule'].id,
            'name': model['syllabus_schedule'].name,
            'description': model['syllabus_schedule'].description,
            'syllabus': model['syllabus_schedule'].syllabus.id,
        } for model in models if model['syllabus_schedule'].id <= 100])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        } for model in models])

    def test_certificate_with_data_with_pagination_first_five(self):
        """Test /certificate without auth"""
        base = self.bc.database.create(authenticate=True)
        models = [
            self.bc.database.create(syllabus_schedule=True, syllabus=True, models=base) for _ in range(0, 10)
        ]
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
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'description': model['syllabus_schedule'].description,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                } for model in models if model['syllabus_schedule'].id <= 5]
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        } for model in models])

    def test_certificate_with_data_with_pagination_last_five(self):
        """Test /certificate without auth"""
        base = self.bc.database.create(authenticate=True)
        models = [
            self.bc.database.create(syllabus_schedule=True, syllabus=True, models=base) for _ in range(0, 10)
        ]
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
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'description': model['syllabus_schedule'].description,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                } for model in models if model['syllabus_schedule'].id > 5],
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        } for model in models])

    def test_certificate_with_data_with_pagination_after_last_five(self):
        """Test /certificate without auth"""
        base = self.bc.database.create(authenticate=True)
        models = [self.bc.database.create(syllabus_schedule=True, models=base) for _ in range(0, 10)]
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
        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        } for model in models])
