"""
Test cases for /academy/member
"""
from unittest.mock import MagicMock, patch
from breathecode.authenticate.models import ProfileAcademy
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from rest_framework.response import Response
from rest_framework import status
from breathecode.utils import capable_of
from ..mixins.new_auth_test_case import AuthTestCase

# the test have too must lines, that's split in many test suite

PROFILE_ACADEMY_STATUS = [
    'INVITED',
    'ACTIVE',
]


@capable_of('read_member')
def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


def format_profile_academy(self, profile_academy, role, academy):
    return {
        'academy': {
            'id': academy.id,
            'name': academy.name,
            'slug': academy.slug
        },
        'address': profile_academy.address,
        'created_at': self.datetime_to_iso(profile_academy.created_at),
        'email': profile_academy.email,
        'first_name': profile_academy.first_name,
        'id': profile_academy.id,
        'last_name': profile_academy.last_name,
        'phone': profile_academy.phone,
        'role': {
            'id': role.slug,
            'name': role.name,
            'slug': role.slug,
        },
        'status': profile_academy.status,
        'user': {
            'email': profile_academy.user.email,
            'first_name': profile_academy.user.first_name,
            'profile': None,
            'id': profile_academy.user.id,
            'last_name': profile_academy.user.last_name
        }
    }


# set of duck tests, the tests about decorators are ignorated in the main test file
class MemberSetOfDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 GET check the param is being passed
    """
    @patch('breathecode.authenticate.views.MemberView.get', MagicMock(side_effect=view_method_mock))
    def test_academy_member__get__with_auth___mock_view(self):
        profile_academies = [{'academy_id': id} for id in range(1, 4)]
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=profile_academies)

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=n)

            url = reverse_lazy('authenticate:academy_member')
            response = self.client.get(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n)}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 POST check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.post', MagicMock(side_effect=view_method_mock))
    def test_academy_member__post__with_auth___mock_view(self):
        profile_academies = [{'academy_id': id} for id in range(1, 4)]
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=profile_academies)

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=n)

            url = reverse_lazy('authenticate:academy_member')
            response = self.client.post(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n)}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 DELETE check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.delete', MagicMock(side_effect=view_method_mock))
    def test_academy_member__delete__with_auth___mock_view(self):
        profile_academies = [{'academy_id': id} for id in range(1, 4)]
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=profile_academies)

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=n)

            url = reverse_lazy('authenticate:academy_member')
            response = self.client.delete(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n)}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class MemberGetTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """
    def test_academy_member_without_auth(self):
        """Test /academy/member without auth"""
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_member_without_capability(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_member "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_member(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)
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
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'profile': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

    """
    🔽🔽🔽 GET with profile
    """

    def test_academy_member__with_profile(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True,
                                        profile=True)
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
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'profile': {
                    'avatar_url': None
                },
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

    """
    🔽🔽🔽 GET with github
    """

    def test_academy_member__with_github(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True,
                                        credentials_github=True)
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
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'profile': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

    """
    🔽🔽🔽 GET query like
    """

    def test_academy_member_query_like_full_name_status_active(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'ACTIVE'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'ACTIVE'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'ACTIVE',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }, {
                             'academy_id': 2,
                             'address': model_2['profile_academy'].address,
                             'email': model_2['profile_academy'].email,
                             'first_name': model_2['profile_academy'].first_name,
                             'id': 2,
                             'last_name': model_2['profile_academy'].last_name,
                             'phone': model_2['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_first_name_status_active(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'ACTIVE'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'ACTIVE'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'ACTIVE',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }, {
                             'academy_id': 2,
                             'address': model_2['profile_academy'].address,
                             'email': model_2['profile_academy'].email,
                             'first_name': model_2['profile_academy'].first_name,
                             'id': 2,
                             'last_name': model_2['profile_academy'].last_name,
                             'phone': model_2['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_last_name_status_active(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'ACTIVE'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'ACTIVE'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'ACTIVE',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }, {
                             'academy_id': 2,
                             'address': model_2['profile_academy'].address,
                             'email': model_2['profile_academy'].email,
                             'first_name': model_2['profile_academy'].first_name,
                             'id': 2,
                             'last_name': model_2['profile_academy'].last_name,
                             'phone': model_2['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_email_status_active(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'ACTIVE'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'ACTIVE'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'ACTIVE',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }, {
                             'academy_id': 2,
                             'address': model_2['profile_academy'].address,
                             'email': model_2['profile_academy'].email,
                             'first_name': model_2['profile_academy'].first_name,
                             'id': 2,
                             'last_name': model_2['profile_academy'].last_name,
                             'phone': model_2['profile_academy'].phone,
                             'role_id': 'hitman',
                             'status': 'ACTIVE',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_full_name_status_invited(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'INVITED'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'INVITED'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
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
                             'role_id': 'hitman',
                             'status': 'INVITED',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_first_name_status_invited(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'INVITED'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'INVITED'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
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
                             'role_id': 'hitman',
                             'status': 'INVITED',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_last_name_status_invited(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'INVITED'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'INVITED'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
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
                             'role_id': 'hitman',
                             'status': 'INVITED',
                             'user_id': 1
                         }])

    def test_academy_member_query_like_email_status_invited(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        base = self.bc.database.create(authenticate=True, role=role, capability='read_member')

        profile_academy_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
            'status': 'INVITED'
        }
        profile_academy_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
            'status': 'INVITED'
        }

        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)
        model_2 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs_2,
                                          models=base)

        base_url = reverse_lazy('authenticate:academy_member')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': {
                'id': model_1['profile_academy'].academy.id,
                'name': model_1['profile_academy'].academy.name,
                'slug': model_1['profile_academy'].academy.slug
            },
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model_1['profile_academy'].user.email,
                'first_name': model_1['profile_academy'].user.first_name,
                'profile': None,
                'id': model_1['profile_academy'].user.id,
                'last_name': model_1['profile_academy'].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             'academy_id': 1,
                             'address': model_1['profile_academy'].address,
                             'email': model_1['profile_academy'].email,
                             'first_name': model_1['profile_academy'].first_name,
                             'id': 1,
                             'last_name': model_1['profile_academy'].last_name,
                             'phone': model_1['profile_academy'].phone,
                             'role_id': 'hitman',
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
                             'role_id': 'hitman',
                             'status': 'INVITED',
                             'user_id': 1
                         }])

    """
    🔽🔽🔽 GET query status
    """

    def test_academy_member__query_status__bad_status(self):
        base = self.bc.database.create(user=1, role=1, capability='read_member')
        for status in PROFILE_ACADEMY_STATUS:
            bad_status = [x for x in PROFILE_ACADEMY_STATUS if status != x][0]
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_member') + f'?status={bad_status}'
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                             self.bc.format.to_dict(model.profile_academy))

            self.bc.database.delete('authenticate.ProfileAcademy')

    def test_academy_member__query_status__one_status__uppercase(self):
        base = self.bc.database.create(user=1, role=1, capability='read_member')
        for status in PROFILE_ACADEMY_STATUS:
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_member') + f'?status={status.upper()}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                format_profile_academy(self, profile_academy, model.role, model.academy)
                for profile_academy in model.profile_academy
            ]

            self.assertEqual(json, expected)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                             self.bc.format.to_dict(model.profile_academy))

            self.bc.database.delete('authenticate.ProfileAcademy')

    def test_academy_member__query_status__one_status__lowercase(self):
        base = self.bc.database.create(user=1, role=1, capability='read_member')
        for status in PROFILE_ACADEMY_STATUS:
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_member') + f'?status={status.lower()}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                format_profile_academy(self, profile_academy, model.role, model.academy)
                for profile_academy in model.profile_academy
            ]

            self.assertEqual(json, expected)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                             self.bc.format.to_dict(model.profile_academy))

            self.bc.database.delete('authenticate.ProfileAcademy')

    """
    🔽🔽🔽 GET query roles
    """

    def test_academy_member_with_zero_roles(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        self.bc.database.create(authenticate=True, role=role, capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        url = f'{url}?roles='
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
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
            'user_id': 1,
        }])

    def test_academy_member_with_one_roles(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        url = f'{url}?roles={role}'
        response = self.client.get(url)
        json = response.json()

        profile_academy = self.get_profile_academy(1)

        self.assertEqual(json, [{
            'academy': {
                'id': model['academy'].id,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
            },
            'address': None,
            'created_at': self.bc.datetime.to_iso_string(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role': {
                'id': role,
                'name': role,
                'slug': role,
            },
            'status': 'INVITED',
            'user': {
                'email': model['user'].email,
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
                'profile': None,
            },
        }])
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
            'user_id': 1,
        }])

    def test_academy_member_with_two_roles(self):
        """Test /academy/:id/member"""
        roles = ['konan', 'pain']
        self.bc.request.set_headers(academy=1)
        models = [
            self.bc.database.create(authenticate=True,
                                    role=roles[0],
                                    capability='read_member',
                                    profile_academy=True)
        ]

        models = models + [
            self.bc.database.create(authenticate=True,
                                    role=roles[1],
                                    capability='read_member',
                                    profile_academy=True,
                                    models={'academy': models[0]['academy']})
        ]
        url = reverse_lazy('authenticate:academy_member')
        args = ','.join(roles)
        url = f'{url}?roles={args}'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'academy': {
                'id': model['academy'].id,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
            },
            'address':
            None,
            'created_at':
            self.bc.datetime.to_iso_string(self.get_profile_academy(model['profile_academy'].id).created_at),
            'email':
            None,
            'first_name':
            None,
            'id':
            model['profile_academy'].id,
            'last_name':
            None,
            'phone':
            '',
            'role': {
                'id': roles[model['profile_academy'].id - 1],
                'name': roles[model['profile_academy'].id - 1],
                'slug': roles[model['profile_academy'].id - 1],
            },
            'status':
            'INVITED',
            'user': {
                'email': model['user'].email,
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
                'profile': None,
            },
        } for model in models])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': None,
            'first_name': None,
            'id': 1 + index,
            'last_name': None,
            'phone': '',
            'role_id': roles[index],
            'status': 'INVITED',
            'user_id': 1 + index,
        } for index in range(0, 2)])


class MemberGetPaginationTestSuite(AuthTestCase):
    def test_academy_member_pagination_with_105(self):
        """Test /academy/member"""
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.bc.database.create(profile_academy=True, models=base) for _ in range(0, 105)]
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
                'id': 'hitman',
                'name': 'hitman',
                'slug': 'hitman'
            },
            'status': 'INVITED',
            'user': {
                'email': model['profile_academy'].user.email,
                'first_name': model['profile_academy'].user.first_name,
                'profile': None,
                'id': model['profile_academy'].user.id,
                'last_name': model['profile_academy'].user.last_name
            }
        } for model in models if model['profile_academy'].id < 101]

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
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
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.bc.database.create(profile_academy=True, models=base) for _ in range(0, 9)]
        url = reverse_lazy('authenticate:academy_member') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            None,
            'last':
            'http://testserver/v1/auth/academy/member?limit=5&offset=5',
            'next':
            'http://testserver/v1/auth/academy/member?limit=5&offset=5',
            'previous':
            None,
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
                    'id': 'hitman',
                    'name': 'hitman',
                    'slug': 'hitman'
                },
                'status': 'INVITED',
                'user': {
                    'email': model['profile_academy'].user.email,
                    'first_name': model['profile_academy'].user.first_name,
                    'profile': None,
                    'id': model['profile_academy'].user.id,
                    'last_name': model['profile_academy'].user.last_name
                }
            } for model in models if model['profile_academy'].id < 6]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
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
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.bc.database.create(profile_academy=True, models=base) for _ in range(0, 9)]
        url = reverse_lazy('authenticate:academy_member') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            'http://testserver/v1/auth/academy/member?limit=5',
            'last':
            None,
            'next':
            None,
            'previous':
            'http://testserver/v1/auth/academy/member?limit=5',
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
                    'id': 'hitman',
                    'name': 'hitman',
                    'slug': 'hitman'
                },
                'status': 'INVITED',
                'user': {
                    'email': model['profile_academy'].user.email,
                    'first_name': model['profile_academy'].user.first_name,
                    'profile': None,
                    'id': model['profile_academy'].user.id,
                    'last_name': model['profile_academy'].user.last_name
                }
            } for model in models if model['profile_academy'].id > 5]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
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
        self.bc.request.set_headers(academy=1)
        role = 'hitman'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_member',
                                        profile_academy=True)

        base = model.copy()
        del base['user']
        del base['profile_academy']

        models = [model] + [self.bc.database.create(profile_academy=True, models=base) for _ in range(0, 9)]
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
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


class MemberPostTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_member_post_no_data(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'role': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
            'user_id': 1,
        }])

    def test_academy_member_post_no_user(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        data = {'role': role}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'user-not-found', 'status_code': 400}
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
            'user_id': 1,
        }])

    def test_academy_member_post_no_invite(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        data = {'role': role, 'invite': True}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'no-email-or-id', 'status_code': 400}
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
            'user_id': 1,
        }])

    def test_academy_member_post_user_with_not_student_role(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        data = {'role': role, 'user': model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'user-already-exists', 'status_code': 400}

        profile_academy = self.get_profile_academy(1)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
            'user_id': 1,
        }])

    def test_academy_member_post_user_with_student_role(self):
        """Test /academy/:id/member"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_member')
        data = {'role': role, 'user': model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()

        profile_academy = self.get_profile_academy(1)
        self.assertEqual(
            json, {
                'address': None,
                'email': profile_academy.email,
                'first_name': 'Kenny',
                'last_name': 'McKornick',
                'phone': '',
                'role': role,
                'status': 'ACTIVE',
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': profile_academy.email,
            'first_name': 'Kenny',
            'id': 1,
            'last_name': 'McKornick',
            'phone': '',
            'role_id': role,
            'status': 'ACTIVE',
            'user_id': 1,
        }])

    def test_academy_member_post_teacher_with_student_role(self):
        """Test /academy/:id/member"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_member',
                                        profile_academy=True)
        model2 = self.bc.database.create(role='teacher', capability='crud_member')
        url = reverse_lazy('authenticate:academy_member')
        data = {'role': 'teacher', 'user': model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()

        profile_academy = self.get_profile_academy(1)
        self.assertEqual(
            json, {
                'address': None,
                'email': profile_academy.email,
                'first_name': 'Kenny',
                'last_name': 'McKornick',
                'phone': '',
                'role': 'teacher',
                'status': 'ACTIVE',
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_profile_academy_dict(), [{
            'academy_id': 1,
            'address': None,
            'email': profile_academy.email,
            'first_name': 'Kenny',
            'id': 1,
            'last_name': 'McKornick',
            'phone': '',
            'role_id': 'teacher',
            'status': 'ACTIVE',
            'user_id': 1,
        }])


class MemberDeleteTestSuite(AuthTestCase):
    """
    🔽🔽🔽 DELETE in bulk
    """
    def test_academy_member_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='crud_member',
                                        role='potato')
        url = reverse_lazy('authenticate:academy_member')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Member not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
            **self.model_to_dict(model, 'profile_academy'),
        }])

    def test_academy_member_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.bc.request.set_headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_member', role='potato')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model = self.bc.database.create(authenticate=True,
                                            profile_academy=True,
                                            profile_academy_kwargs=profile_academy_kwargs,
                                            models=base)

            url = (reverse_lazy('authenticate:academy_member') + f'?{field}=' +
                   str(getattr(model['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    def test_academy_member_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.bc.request.set_headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_member', role='potato')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model1 = self.bc.database.create(authenticate=True,
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
            model2 = self.bc.database.create(profile_academy=True,
                                             profile_academy_kwargs=profile_academy_kwargs,
                                             models=base)

            url = (reverse_lazy('authenticate:academy_member') + f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    def test_academy_member_delete_in_bulk_with_two_but_is_student(self):
        """Test /cohort/:id/user without auth"""
        self.bc.request.set_headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_member', role='student')

        for field in many_fields:
            profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
                'address': choice(['asd', 'qwe', 'zxc']),
                'phone': choice(['123', '456', '789']),
                'status': choice(['INVITED', 'ACTIVE']),
            }
            model1 = self.bc.database.create(authenticate=True,
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
            model2 = self.bc.database.create(profile_academy=True,
                                             profile_academy_kwargs=profile_academy_kwargs,
                                             models=base)

            url = (reverse_lazy('authenticate:academy_member') + f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
                **self.model_to_dict(model1, 'profile_academy'),
            }, {
                **self.model_to_dict(model2, 'profile_academy'),
            }])

            for model in ProfileAcademy.objects.all():
                model.delete()
