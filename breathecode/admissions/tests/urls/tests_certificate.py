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
        url = reverse_lazy('admissions:certificate')
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
        url = reverse_lazy('admissions:certificate')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_specialty_mode(), 0)

    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True, specialty_mode=True)
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['specialty_mode'].id,
            'name': model['specialty_mode'].name,
            'slug': model['specialty_mode'].slug,
            'description': model['specialty_mode'].description,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        }])

    def test_certificate_with_data_without_pagination_get_just_100(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, models=base) for _ in range(0, 105)]
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['specialty_mode'].id,
            'name': model['specialty_mode'].name,
            'slug': model['specialty_mode'].slug,
            'description': model['specialty_mode'].description,
        } for model in models if model['specialty_mode'].id <= 100])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_first_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count':
                10,
                'first':
                None,
                'last':
                'http://testserver/v1/admissions/certificate?limit=5&offset=5',
                'next':
                'http://testserver/v1/admissions/certificate?limit=5&offset=5',
                'previous':
                None,
                'results': [{
                    'id': model['specialty_mode'].id,
                    'name': model['specialty_mode'].name,
                    'slug': model['specialty_mode'].slug,
                    'description': model['specialty_mode'].description,
                } for model in models if model['specialty_mode'].id <= 5]
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count':
                10,
                'first':
                'http://testserver/v1/admissions/certificate?limit=5',
                'last':
                None,
                'next':
                None,
                'previous':
                'http://testserver/v1/admissions/certificate?limit=5',
                'results': [{
                    'id': model['specialty_mode'].id,
                    'name': model['specialty_mode'].name,
                    'slug': model['specialty_mode'].slug,
                    'description': model['specialty_mode'].description,
                } for model in models if model['specialty_mode'].id > 5]
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_with_data_with_pagination_after_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(specialty_mode=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'count': 10,
                'first': 'http://testserver/v1/admissions/certificate?limit=5',
                'last': None,
                'next': None,
                'previous': 'http://testserver/v1/admissions/certificate?limit=5&offset=5',
                'results': [],
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        } for model in models])

    def test_certificate_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:certificate')
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
        url = reverse_lazy('admissions:academy_certificate')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': "Missing parameters in the querystring", 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_dict(), [])

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
            url = (reverse_lazy('admissions:academy_certificate') + f'?{field}=' +
                   str(getattr(model['specialty_mode'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
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

            url = (reverse_lazy('admissions:academy_certificate') + f'?{field}=' +
                   str(getattr(model1['specialty_mode'], field)) + ',' +
                   str(getattr(model2['specialty_mode'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_specialty_mode_dict(), [])
