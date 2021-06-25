"""
Test cases for /academy/:id/member/:id
"""
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member/:id without auth"""
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id': 2
                           })
        data = {'email': self.email, 'password': self.password}
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_id_member_id_without_capability(self):
        """Test /academy/:id/member/:id"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id': 2
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 2) don't have this capability: read_member "
                "for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_id_member_id_without_academy(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.generate_models(authenticate=True,
                             role=role,
                             capability='read_member')
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id': 2
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 2) don't have this capability: read_member "
                "for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_id_member_id(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id': 2
                           })
        response = self.client.get(url)
        json = response.json()

        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(
                    profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
                'last_name': None,
                'phone': '',
                'role': {
                    'name': role,
                    'slug': role,
                },
                'status': 'INVITED',
                'user': {
                    'email': model['user'].email,
                    'first_name': model['user'].first_name,
                    'id': model['user'].id,
                    'last_name': model['user'].last_name,
                    'github': None,
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': 1,
            'last_name': None,
            'phone': '',
            'role_id': role,
            'status': 'INVITED',
            'user_id': 2,
        }])

    def test_academy_id_member_id_with_github(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True,
                                     credentials_github=True)
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id': 2
                           })
        response = self.client.get(url)
        json = response.json()

        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(
                    profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
                'last_name': None,
                'phone': '',
                'role': {
                    'name': role,
                    'slug': role,
                },
                'status': 'INVITED',
                'user': {
                    'email': model['user'].email,
                    'first_name': model['user'].first_name,
                    'id': model['user'].id,
                    'last_name': model['user'].last_name,
                    'github': {
                        'avatar_url': None,
                        'name': None,
                        'username': None
                    },
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': 1,
            'last_name': None,
            'phone': '',
            'role_id': role,
            'status': 'INVITED',
            'user_id': 2,
        }])
