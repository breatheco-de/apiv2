"""
Test cases for /academy/student
"""
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from ...models import ProfileAcademy
from ..mixins.new_auth_test_case import AuthTestCase


# TODO: this test is incompleted
class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_student_without_auth(self):
        """Test /academy/student without auth"""
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_student_without_capability(self):
        """Test /academy/student"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: read_student "
                "for academy 1",
                'status_code':
                403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_student_without_academy(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        self.generate_models(authenticate=True,
                             role=role,
                             capability='read_student')
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: read_student "
                "for academy 1",
                'status_code':
                403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_student_without_student(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': 1,
            'last_name': None,
            'phone': '',
            'role_id': 'konan',
            'status': 'INVITED',
            'user_id': 1
        }])

    def test_academy_student(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model['profile_academy'].academy.id,
                'name': model['profile_academy'].academy.name,
                'slug': model['profile_academy'].academy.slug
            },
            'address':
            model['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model['profile_academy'].created_at),
            'email':
            model['profile_academy'].email,
            'first_name':
            model['profile_academy'].first_name,
            'id':
            model['profile_academy'].id,
            'last_name':
            model['profile_academy'].last_name,
            'phone':
            model['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'github': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': 1,
            'last_name': None,
            'phone': '',
            'role_id': 'student',
            'status': 'INVITED',
            'user_id': 1
        }])

    def test_academy_student_pagination_with_105(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [
            self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 105)
        ]
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model['profile_academy'].academy.id,
                'name': model['profile_academy'].academy.name,
                'slug': model['profile_academy'].academy.slug
            },
            'address':
            model['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model['profile_academy'].created_at),
            'email':
            model['profile_academy'].email,
            'first_name':
            model['profile_academy'].first_name,
            'id':
            model['profile_academy'].id,
            'last_name':
            model['profile_academy'].last_name,
            'phone':
            model['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'github': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        } for model in models if model['profile_academy'].id < 101]

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(),
                         [{
                             'academy_id': 1,
                             'address': None,
                             'email': None,
                             'first_name': None,
                             'id': model['profile_academy'].id,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'student',
                             'status': 'INVITED',
                             'user_id': model['user'].id
                         } for model in models])

    def test_academy_student_pagination_first_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [
            self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)
        ]
        url = reverse_lazy(
            'authenticate:academy_student') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            None,
            'last':
            'http://testserver/v1/auth/academy/student?limit=5&offset=5',
            'next':
            'http://testserver/v1/auth/academy/student?limit=5&offset=5',
            'previous':
            None,
            'results': [{
                'academy': {
                    'id': model['profile_academy'].academy.id,
                    'name': model['profile_academy'].academy.name,
                    'slug': model['profile_academy'].academy.slug
                },
                'address':
                model['profile_academy'].address,
                'created_at':
                self.datetime_to_iso(model['profile_academy'].created_at),
                'email':
                model['profile_academy'].email,
                'first_name':
                model['profile_academy'].first_name,
                'id':
                model['profile_academy'].id,
                'last_name':
                model['profile_academy'].last_name,
                'phone':
                model['profile_academy'].phone,
                'role': {
                    'name': 'student',
                    'slug': 'student'
                },
                'status':
                'INVITED',
                'user': {
                    'email': model['profile_academy'].user.email,
                    'first_name': model['profile_academy'].user.first_name,
                    'github': None,
                    'id': model['profile_academy'].user.id,
                    'last_name': model['profile_academy'].user.last_name
                }
            } for model in models if model['profile_academy'].id < 6]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(),
                         [{
                             'academy_id': 1,
                             'address': None,
                             'email': None,
                             'first_name': None,
                             'id': model['profile_academy'].id,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'student',
                             'status': 'INVITED',
                             'user_id': model['user'].id
                         } for model in models])

    def test_academy_student_pagination_last_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [
            self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)
        ]
        url = reverse_lazy(
            'authenticate:academy_student') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            'http://testserver/v1/auth/academy/student?limit=5',
            'last':
            None,
            'next':
            None,
            'previous':
            'http://testserver/v1/auth/academy/student?limit=5',
            'results': [{
                'academy': {
                    'id': model['profile_academy'].academy.id,
                    'name': model['profile_academy'].academy.name,
                    'slug': model['profile_academy'].academy.slug
                },
                'address':
                model['profile_academy'].address,
                'created_at':
                self.datetime_to_iso(model['profile_academy'].created_at),
                'email':
                model['profile_academy'].email,
                'first_name':
                model['profile_academy'].first_name,
                'id':
                model['profile_academy'].id,
                'last_name':
                model['profile_academy'].last_name,
                'phone':
                model['profile_academy'].phone,
                'role': {
                    'name': 'student',
                    'slug': 'student'
                },
                'status':
                'INVITED',
                'user': {
                    'email': model['profile_academy'].user.email,
                    'first_name': model['profile_academy'].user.first_name,
                    'github': None,
                    'id': model['profile_academy'].user.id,
                    'last_name': model['profile_academy'].user.last_name
                }
            } for model in models if model['profile_academy'].id > 5]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(),
                         [{
                             'academy_id': 1,
                             'address': None,
                             'email': None,
                             'first_name': None,
                             'id': model['profile_academy'].id,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'student',
                             'status': 'INVITED',
                             'user_id': model['user'].id
                         } for model in models])

    def test_academy_student_pagination_after_last_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [
            self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)
        ]
        url = reverse_lazy(
            'authenticate:academy_student') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/auth/academy/student?limit=5',
            'last': None,
            'next': None,
            'previous':
            'http://testserver/v1/auth/academy/student?limit=5&offset=5',
            'results': []
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(),
                         [{
                             'academy_id': 1,
                             'address': None,
                             'email': None,
                             'first_name': None,
                             'id': model['profile_academy'].id,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'student',
                             'status': 'INVITED',
                             'user_id': model['user'].id
                         } for model in models])

    def test_academy_student_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': 401
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_header(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail':
            'Missing academy_id parameter expected for the endpoint url or \'Academy\' header',
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_capability(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail':
            "You (user: 1) don't have this capability: crud_student for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_student',
                                     role='student')
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'details': "Missing user_id or academy_id",
            'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_profile_academy_dict(), [{
            **self.model_to_dict(model, 'profile_academy'),
        }])

    def test_academy_student_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True,
                                    capability='crud_student',
                                    role='student')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model = self.generate_models(
                authenticate=True,
                profile_academy=True,
                profile_academy_kwargs=profile_academy_kwargs,
                models=base)

            url = (reverse_lazy('authenticate:academy_student') +
                   f'?{field}=' +
                   str(getattr(model['profile_academy'], field)))
            response = self.client.delete(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True,
                                    capability='crud_student',
                                    role='student')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model1 = self.generate_models(
                authenticate=True,
                profile_academy=True,
                profile_academy_kwargs=profile_academy_kwargs,
                models=base)

            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model2 = self.generate_models(
                profile_academy=True,
                profile_academy_kwargs=profile_academy_kwargs,
                models=base)

            url = (reverse_lazy('authenticate:academy_student') +
                   f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_in_bulk_with_two_but_is_not_student(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True,
                                    capability='crud_student',
                                    role='hitman')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model1 = self.generate_models(
                authenticate=True,
                profile_academy=True,
                profile_academy_kwargs=profile_academy_kwargs,
                models=base)

            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model2 = self.generate_models(
                profile_academy=True,
                profile_academy_kwargs=profile_academy_kwargs,
                models=base)

            url = (reverse_lazy('authenticate:academy_student') +
                   f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [{
                **self.model_to_dict(model1, 'profile_academy'),
            }, {
                **self.model_to_dict(model2, 'profile_academy'),
            }])

            for model in ProfileAcademy.objects.all():
                model.delete()

    def test_academy_student_query_like_full_name(self):
        """Test /academy/student"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    role='student',
                                    capability='read_student')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Rene',
            'last_name': 'Lopez',
        }
        model_1 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs,
            models=base)

        model_2 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs_2,
            models=base)

        base_url = reverse_lazy('authenticate:academy_student')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address':
            model_1['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email':
            model_1['profile_academy'].email,
            'first_name':
            model_1['profile_academy'].first_name,
            'id':
            model_1['profile_academy'].id,
            'last_name':
            model_1['profile_academy'].last_name,
            'phone':
            model_1['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'github': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(
            self.all_profile_academy_dict(),
            [{
                'academy_id': 1,
                'address': model_1['profile_academy'].address,
                'email': model_1['profile_academy'].email,
                'first_name': model_1['profile_academy'].first_name,
                'id': 1,
                'last_name': model_1['profile_academy'].last_name,
                'phone': model_1['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }, {
                'academy_id': 2,
                'address': model_2['profile_academy'].address,
                'email': model_2['profile_academy'].email,
                'first_name': model_2['profile_academy'].first_name,
                'id': 2,
                'last_name': model_2['profile_academy'].last_name,
                'phone': model_2['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }])

    def test_academy_student_query_like_first_name(self):
        """Test /academy/student"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    role='student',
                                    capability='read_student')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        model_1 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs,
            models=base)

        model_2 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs_2,
            models=base)

        base_url = reverse_lazy('authenticate:academy_student')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address':
            model_1['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email':
            model_1['profile_academy'].email,
            'first_name':
            model_1['profile_academy'].first_name,
            'id':
            model_1['profile_academy'].id,
            'last_name':
            model_1['profile_academy'].last_name,
            'phone':
            model_1['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'github': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(
            self.all_profile_academy_dict(),
            [{
                'academy_id': 1,
                'address': model_1['profile_academy'].address,
                'email': model_1['profile_academy'].email,
                'first_name': model_1['profile_academy'].first_name,
                'id': 1,
                'last_name': model_1['profile_academy'].last_name,
                'phone': model_1['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }, {
                'academy_id': 2,
                'address': model_2['profile_academy'].address,
                'email': model_2['profile_academy'].email,
                'first_name': model_2['profile_academy'].first_name,
                'id': 2,
                'last_name': model_2['profile_academy'].last_name,
                'phone': model_2['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }])

    def test_academy_student_query_like_last_name(self):
        """Test /academy/student"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    role='student',
                                    capability='read_student')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        model_1 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs,
            models=base)

        model_2 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs_2,
            models=base)

        base_url = reverse_lazy('authenticate:academy_student')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address':
            model_1['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email':
            model_1['profile_academy'].email,
            'first_name':
            model_1['profile_academy'].first_name,
            'id':
            model_1['profile_academy'].id,
            'last_name':
            model_1['profile_academy'].last_name,
            'phone':
            model_1['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'github': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(
            self.all_profile_academy_dict(),
            [{
                'academy_id': 1,
                'address': model_1['profile_academy'].address,
                'email': model_1['profile_academy'].email,
                'first_name': model_1['profile_academy'].first_name,
                'id': 1,
                'last_name': model_1['profile_academy'].last_name,
                'phone': model_1['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }, {
                'academy_id': 2,
                'address': model_2['profile_academy'].address,
                'email': model_2['profile_academy'].email,
                'first_name': model_2['profile_academy'].first_name,
                'id': 2,
                'last_name': model_2['profile_academy'].last_name,
                'phone': model_2['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }])

    def test_academy_student_query_like_email(self):
        """Test /academy/student"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    role='student',
                                    capability='read_student')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        model_1 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs,
            models=base)

        model_2 = self.generate_models(
            profile_academy=True,
            profile_academy_kwargs=profile_academy_kwargs_2,
            models=base)

        base_url = reverse_lazy('authenticate:academy_student')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address':
            model_1['profile_academy'].address,
            'created_at':
            self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email':
            model_1['profile_academy'].email,
            'first_name':
            model_1['profile_academy'].first_name,
            'id':
            model_1['profile_academy'].id,
            'last_name':
            model_1['profile_academy'].last_name,
            'phone':
            model_1['profile_academy'].phone,
            'role': {
                'name': 'student',
                'slug': 'student'
            },
            'status':
            'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'github': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(
            self.all_profile_academy_dict(),
            [{
                'academy_id': 1,
                'address': model_1['profile_academy'].address,
                'email': model_1['profile_academy'].email,
                'first_name': model_1['profile_academy'].first_name,
                'id': 1,
                'last_name': model_1['profile_academy'].last_name,
                'phone': model_1['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }, {
                'academy_id': 2,
                'address': model_2['profile_academy'].address,
                'email': model_2['profile_academy'].email,
                'first_name': model_2['profile_academy'].first_name,
                'id': 2,
                'last_name': model_2['profile_academy'].last_name,
                'phone': model_2['profile_academy'].phone,
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 1
            }])
