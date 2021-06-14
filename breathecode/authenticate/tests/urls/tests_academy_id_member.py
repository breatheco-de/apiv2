"""
Test cases for /academy/:id/member
"""
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_id_member_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = { 'email': self.email, 'password': self.password }
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_id_member_without_capability(self):
        """Test /academy/:id/member"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 2) don't have this capability: read_member "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_id_member_without_academy(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.generate_models(authenticate=True, role=role,
            capability='read_member')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 2) don't have this capability: read_member "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_id_member(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'created_at': datetime_to_iso_format(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_github(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True,
            credentials_github=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'created_at': datetime_to_iso_format(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
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
                'github': {'avatar_url': None, 'name': None, 'username': None},
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_status_invited(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True,
            profile_academy_status='INVITED')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        url = f'{url}?status=INVITED'
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
            'created_at': datetime_to_iso_format(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_status_invited_without_data(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True,
            profile_academy_status='ACTIVE')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        url = f'{url}?status=INVITED'
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
            'status': 'ACTIVE',
            'user_id': 2,
        }])

    def test_academy_id_member_with_status_active(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True,
            profile_academy_status='ACTIVE')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        url = f'{url}?status=ACTIVE'
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
            'created_at': datetime_to_iso_format(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role': {
                'name': role,
                'slug': role,
            },
            'status': 'ACTIVE',
            'user': {
                'email': model['user'].email,
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
                'github': None,
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
            'status': 'ACTIVE',
            'user_id': 2,
        }])

    def test_academy_id_member_with_status_active_without_data(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True,
            profile_academy_status='INVITED')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        url = f'{url}?status=ACTIVE'
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_zero_roles(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_zero_roles(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_one_roles(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='read_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'created_at': datetime_to_iso_format(profile_academy.created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
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
            'user_id': 2,
        }])

    def test_academy_id_member_with_two_roles(self):
        """Test /academy/:id/member"""
        roles = ['konan', 'pain']
        models = [self.generate_models(authenticate=True, role=roles[0],
            capability='read_member', profile_academy=True)]

        models = models + [self.generate_models(authenticate=True, role=roles[1],
            capability='read_member', profile_academy=True, models={'academy': models[0]['academy']})]
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'address': None,
            'created_at': datetime_to_iso_format(self.get_profile_academy(
                model['profile_academy'].id).created_at),
            'email': None,
            'first_name': None,
            'id': model['profile_academy'].id,
            'last_name': None,
            'phone': '',
            'role': {
                'name': roles[model['profile_academy'].id - 1],
                'slug': roles[model['profile_academy'].id - 1],
            },
            'status': 'INVITED',
            'user': {
                'email': model['user'].email,
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
                'github': None,
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
            'user_id': 2 + index,
        } for index in range(0, 2)])

    def test_academy_id_member_post_no_data(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
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
            'user_id': 2,
        }])

    def test_academy_id_member_post_no_user(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = {'role': role}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': "user-not-found", 'status_code' : 400}
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
            'user_id': 2,
        }])

    def test_academy_id_member_post_no_invite(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = {'role': role, 'invite': True}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': "no-email-or-id",
            'status_code' : 400}
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
            'user_id': 2,
        }])

    def test_academy_id_member_post_user_with_not_student_role(self):
        """Test /academy/:id/member"""
        role = 'konan'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = { 'role': role , 'user' : model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'user-already-exists','status_code' : 400}

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
            'user_id': 2,
        }])

    def test_academy_id_member_post_user_with_student_role(self):
        """Test /academy/:id/member"""
        role = 'student'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = { 'role': role , 'user' : model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()

        profile_academy = self.get_profile_academy(1)
        self.assertEqual(json, {
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
            'user_id': 2,
        }])

    def test_academy_id_member_post_teacher_with_student_role(self):
        """Test /academy/:id/member"""
        role = 'student'
        model = self.generate_models(authenticate=True, role=role,
            capability='crud_member', profile_academy=True)
        model2 = self.generate_models(role='teacher', capability='crud_member')
        url = reverse_lazy('authenticate:academy_id_member', kwargs={'academy_id':1})
        data = { 'role': 'teacher' , 'user' : model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()

        profile_academy = self.get_profile_academy(1)
        self.assertEqual(json, {
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
            'user_id': 2,
        }])