"""
Test cases for /academy/member
"""
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


# TODO: this test is incompleted
class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_member_without_auth(self):
        """Test /academy/member without auth"""
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_member_without_capability(self):
        """Test /academy/member"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_member "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_member_without_academy(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'konan'
        self.generate_models(authenticate=True, role=role,
            capability='read_member')
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_member "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_member(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'hitman'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model['profile_academy'].academy.id,
                'name': model['profile_academy'].academy.name,
                'slug': model['profile_academy'].academy.slug
            },
            'address': model['profile_academy'].address,
            'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
            'email': model['profile_academy'].email,
            'first_name': model['profile_academy'].first_name,
            'id': model['profile_academy'].id,
            'last_name': model['profile_academy'].last_name,
            'phone': model['profile_academy'].phone,
            'role': {
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
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
            'role_id': 'hitman',
            'status': 'INVITED',
            'user_id': 1
        }])

    def test_academy_member_pagination_with_105(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'hitman'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 105)]
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model['profile_academy'].academy.id,
                'name': model['profile_academy'].academy.name,
                'slug': model['profile_academy'].academy.slug
            },
            'address': model['profile_academy'].address,
            'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
            'email': model['profile_academy'].email,
            'first_name': model['profile_academy'].first_name,
            'id': model['profile_academy'].id,
            'last_name': model['profile_academy'].last_name,
            'phone': model['profile_academy'].phone,
            'role': {
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'github': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        } for model in models if model['profile_academy'].id < 101]

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role_id': 'hitman',
            'status': 'INVITED',
            'user_id': model['user'].id
        } for model in models])

    def test_academy_member_pagination_first_five(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'hitman'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)]
        url = reverse_lazy('authenticate:academy_member') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': None,
            'last': 'http://testserver/v1/auth/academy/member?limit=5&offset=5',
            'next': 'http://testserver/v1/auth/academy/member?limit=5&offset=5',
            'previous': None,
            'results': [{
                'academy': {
                    'id': model['profile_academy'].academy.id,
                    'name': model['profile_academy'].academy.name,
                    'slug': model['profile_academy'].academy.slug
                },
                'address': model['profile_academy'].address,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'phone': model['profile_academy'].phone,
                'role': {
                    'name': 'hitman',
                    'slug': 'hitman'
                },
                'status': 'INVITED',
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
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role_id': 'hitman',
            'status': 'INVITED',
            'user_id': model['user'].id
        } for model in models])

    def test_academy_member_pagination_last_five(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'hitman'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)]
        url = reverse_lazy('authenticate:academy_member') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/auth/academy/member?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/auth/academy/member?limit=5',
            'results': [{
                'academy': {
                    'id': model['profile_academy'].academy.id,
                    'name': model['profile_academy'].academy.name,
                    'slug': model['profile_academy'].academy.slug
                },
                'address': model['profile_academy'].address,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'phone': model['profile_academy'].phone,
                'role': {
                    'name': 'hitman',
                    'slug': 'hitman'
                },
                'status': 'INVITED',
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
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role_id': 'hitman',
            'status': 'INVITED',
            'user_id': model['user'].id
        } for model in models])

    def test_academy_member_pagination_after_last_five(self):
        """Test /academy/member"""
        self.headers(academy=1)
        role = 'hitman'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.generate_models(profile_academy=True, models=base)
            for _ in range(0, 9)]
        url = reverse_lazy('authenticate:academy_member') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/auth/academy/member?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/auth/academy/member?limit=5&offset=5',
            'results': []
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role_id': 'hitman',
            'status': 'INVITED',
            'user_id': model['user'].id
        } for model in models])

