"""
Test cases for /academy/:id/member/:id
"""
from unittest.mock import MagicMock, patch
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id_without_auth(self):
        """Test /academy/:id/member/:id without auth"""
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id_without_capability(self):
        """Test /academy/:id/member/:id"""
        self.headers(academy=1)

        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_student "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data, passing id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__passing_id__not_found(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '2'})
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

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__passing_id(self):
        """Test /academy/:id/member/:id"""
        self.headers(academy=1)
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'invite_url': 'https://dotdotdotdotdot.dot/v1/auth/academy/html/invite',
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

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__passing_email(self):
        """Test /academy/:id/member/:id"""
        self.headers(academy=1)
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': model.user.email})
        response = self.client.get(url)
        json = response.json()
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'invite_url': 'https://dotdotdotdotdot.dot/v1/auth/academy/html/invite',
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

    """
    🔽🔽🔽 GET with profile ans github
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__with_profile__with_github(self):
        """Test /academy/:id/member/:id"""
        self.headers(academy=1)
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True,
                                     credentials_github=True,
                                     profile=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()
        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'invite_url': 'https://dotdotdotdotdot.dot/v1/auth/academy/html/invite',
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

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id_with_github(self):
        """Test /academy/:id/member/:id"""
        self.headers(academy=1)
        role = 'konan'
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='read_student',
                                     profile_academy=True,
                                     credentials_github=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.get(url)
        json = response.json()

        profile_academy = self.get_profile_academy(1)

        self.assertEqual(
            json, {
                'invite_url': 'https://dotdotdotdotdot.dot/v1/auth/academy/html/invite',
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

    """
    🔽🔽🔽 PUT capability
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__without_capability(self):
        """Test /academy/:id/member/:id"""
        self.bc.request.set_headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: crud_student "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT passing email
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__passing_email(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': 'dude@dude.dude'})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'user-id-is-not-numeric', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT user not exists
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__user_does_not_exists(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '2'})

        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT changing role
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__changing_role(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(role=role, user=1, capability='crud_student', profile_academy=True)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})

        data = {'role': 'nut'}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'trying-to-change-role', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT changing a staff
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__changing_a_staff(self):
        """Test /academy/:id/member/:id"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(role=role, user=1, capability='crud_student', profile_academy=True)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})

        data = {}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'trying-to-change-a-staff', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT User exists but without a ProfileAcademy
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__user_exists_but_without_profile_academy(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(role=role, user=2, capability='crud_student', profile_academy=True)

        self.bc.request.authenticate(model.user[0])
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '2'})

        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 PUT with data
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__put__with_data(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})

        response = self.client.put(url)

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
    def test_academy_student_id__put__with_data__changing_values(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})

        data = {'first_name': 'Lord', 'last_name': 'Valdomero'}
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
    def test_academy_student_id__delete__passing_email(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': 'dude@dude.dude'})
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

    """
    🔽🔽🔽 DELETE with data, passing id and bulk mode
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__delete__passing_id_and_bulk_mode(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'}) + '?id=1,2,3'
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

    """
    🔽🔽🔽 DELETE with data, passing bad id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__delete__passing_bad_id(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '2'})
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

    """
    🔽🔽🔽 DELETE with data, passing id
    """

    @patch('os.getenv', MagicMock(return_value='https://dotdotdotdotdot.dot'))
    def test_academy_student_id__delete__passing_id(self):
        """Test /academy/:id/member/:id"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     role=role,
                                     capability='crud_student',
                                     profile_academy=True)
        url = reverse_lazy('authenticate:academy_student_id', kwargs={'user_id_or_email': '1'})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
