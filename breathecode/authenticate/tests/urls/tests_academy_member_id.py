"""
Test cases for /academy/:id/member/:id
"""
import os
import urllib.parse
import breathecode.notify.actions as actions
from unittest.mock import MagicMock, patch
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.response import Response
from breathecode.utils import capable_of
from ..mixins.new_auth_test_case import AuthTestCase


@capable_of('read_member')
def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


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

            url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': f'{n}'})
            response = self.client.get(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n), 'user_id_or_email': f'{n}'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 PUT check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.put', MagicMock(side_effect=view_method_mock))
    def test_academy_member__put__with_auth___mock_view(self):
        profile_academies = [{'academy_id': id} for id in range(1, 4)]
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=profile_academies)

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=n)

            url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': f'{n}'})
            response = self.client.put(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n), 'user_id_or_email': f'{n}'}}

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

            url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': f'{n}'})
            response = self.client.delete(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': str(n), 'user_id_or_email': f'{n}'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id_without_auth(self):
        """Test /academy/:id/member/:id without auth"""
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id_without_capability(self):
        """Test /academy/:id/member/:id"""
        self.bc.request.set_headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_member "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id_without_academy(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        self.generate_models(authenticate=True, role=role, capability='read_member')
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_member "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data, passing id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__passing_id__not_found(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '2'})
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

    """
    🔽🔽🔽 GET with data, passing id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__passing_id(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()
        del json['invite_url']  # removing this because i will not hardcode it on the test
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
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
                    'github': None,
                    'profile': None,
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET without data, passing email
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__passing_email__not_found(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': 'dude@dude.dude'})
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET with data, passing email
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__passing_id(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        email = 'dude@dude.dude'
        user = {'email': email}
        model = self.generate_models(authenticate=True,
                                     user=user,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': email})
        response = self.client.get(url)
        json = response.json()
        del json['invite_url']  # removing this because i will not hardcode it on the test
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
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
                    'github': None,
                    'profile': None,
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET with profile and github
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__with_profile__with_github(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True,
                                     credentials_github=True,
                                     profile=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()
        del json['invite_url']  # removing this because i will not hardcode it on the test
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
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
                    'github': {
                        'avatar_url': model['user'].credentialsgithub.avatar_url,
                        'name': model['user'].credentialsgithub.name,
                        'username': model['user'].credentialsgithub.username,
                    },
                    'profile': {
                        'avatar_url': model['user'].profile.avatar_url
                    },
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET with github
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id_with_github(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_member',
                                     profile_academy=True,
                                     credentials_github=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()
        del json['invite_url']  # removing this because i will not hardcode it on the test
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'address': None,
                'created_at': datetime_to_iso_format(profile_academy.created_at),
                'email': None,
                'first_name': None,
                'id': 1,
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
                    'github': {
                        'avatar_url': None,
                        'name': None,
                        'username': None
                    },
                    'profile': None,
                },
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 PUT capability
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__without_capability(self):
        """Test /academy/:id/member/:id"""
        self.bc.request.set_headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: crud_member "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT passing email
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__passing_email(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': 'dude@dude.dude'})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'user-id-is-not-numeric', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT without required fields
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__without_required_fields(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})

        response = self.client.put(url)
        json = response.json()
        expected = {'role': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT user not exists, it's use the post serializer
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__user_does_not_exists(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '2'})

        data = {'role': role}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'user-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT User exists but without a ProfileAcademy, it's use the post serializer
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__user_exists_but_without_profile_academy(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(role=role, user=2, capability='crud_member', profile_academy=True)

        self.bc.request.authenticate(model.user[0])
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '2'})

        data = {'role': role}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {
            'address': None,
            'email': model.user[1].email,
            'first_name': None,
            'last_name': None,
            'phone': '',
            'role': role,
            'status': 'ACTIVE',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
            {
                **self.bc.format.to_dict(model.profile_academy),
                'id': 2,
                'email': model.user[1].email,
                'first_name': None,
                'last_name': None,
                'role_id': role,
                'status': 'ACTIVE',
                'user_id': 2,
            },
        ])

    """
    🔽🔽🔽 PUT with data
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__with_data(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})

        data = {'role': role}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {
            'academy': model.academy.id,
            'address': model.profile_academy.address,
            'first_name': model.profile_academy.first_name,
            'last_name': model.profile_academy.last_name,
            'phone': model.profile_academy.phone,
            'role': role,
            'user': model.user.id,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT with data, changing values
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__put__with_data__changing_values(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})

        data = {'role': role, 'first_name': 'Lord', 'last_name': 'Valdomero'}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {
            'academy': model.academy.id,
            'address': model.profile_academy.address,
            'first_name': 'Lord',
            'last_name': 'Valdomero',
            'phone': model.profile_academy.phone,
            'role': role,
            'user': model.user.id,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            {
                **self.bc.format.to_dict(model.profile_academy),
                'first_name': 'Lord',
                'last_name': 'Valdomero',
            },
        ])

    """
    🔽🔽🔽 DELETE with data, passing email
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__delete__passing_email(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': 'dude@dude.dude'})
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'user-id-is-not-numeric', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 DELETE with data, passing id and bulk mode
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__delete__passing_id_and_bulk_mode(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'}) + '?id=1,2,3'
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'user-id-and-bulk-mode', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 DELETE with data, passing bad id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__delete__passing_bad_id(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '2'})
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [{
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

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 DELETE with data, passing id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_member_id__delete__passing_id(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_member',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_member_id', kwargs={'user_id_or_email': '1'})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
