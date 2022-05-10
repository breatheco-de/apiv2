"""
Test cases for /academy/student
"""
import os
import urllib.parse
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from django.utils import timezone
from random import choice
import breathecode.notify.actions as actions
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ...models import ProfileAcademy
from ..mixins.new_auth_test_case import AuthTestCase

PROFILE_ACADEMY_STATUS = [
    'INVITED',
    'ACTIVE',
]


def generate_user_invite(data: dict) -> dict:
    return {
        'academy_id': None,
        'author_id': None,
        'cohort_id': None,
        'email': None,
        'first_name': None,
        'id': 0,
        'last_name': None,
        'phone': '',
        'role_id': None,
        'sent_at': None,
        'status': 'PENDING',
        'token': '',
        **data,
    }


UTC_NOW = timezone.now()


def getrandbits(n):
    return int(n * (10**37) + n)


TOKEN = str(getrandbits(128))


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


class StudentGetTestSuite(AuthTestCase):
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
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_student "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_student_without_academy(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        self.bc.database.create(authenticate=True, role=role, capability='read_student')
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_student "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_student_without_student(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        model = self.bc.database.create(authenticate=True,
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
        model = self.bc.database.create(authenticate=True,
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
            'address': model['profile_academy'].address,
            'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
            'email': model['profile_academy'].email,
            'first_name': model['profile_academy'].first_name,
            'id': model['profile_academy'].id,
            'last_name': model['profile_academy'].last_name,
            'phone': model['profile_academy'].phone,
            'role': {
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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

    """
    🔽🔽🔽 With profile
    """

    def test_academy_student__with_profile(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_student',
                                        profile_academy=True,
                                        profile=True)
        url = reverse_lazy('authenticate:academy_student')
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
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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

    """
    🔽🔽🔽 GET query like
    """

    def test_academy_student_query_like_full_name(self):
        """Test /academy/student"""
        self.headers(academy=1)
        base = self.bc.database.create(authenticate=True, role='student', capability='read_student')

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
        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)

        model_2 = self.bc.database.create(profile_academy=True,
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
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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
        self.assertEqual(self.all_profile_academy_dict(), [{
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
        base = self.bc.database.create(authenticate=True, role='student', capability='read_student')

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
        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)

        model_2 = self.bc.database.create(profile_academy=True,
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
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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
        self.assertEqual(self.all_profile_academy_dict(), [{
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
        base = self.bc.database.create(authenticate=True, role='student', capability='read_student')

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
        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)

        model_2 = self.bc.database.create(profile_academy=True,
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
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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
        self.assertEqual(self.all_profile_academy_dict(), [{
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
        base = self.bc.database.create(authenticate=True, role='student', capability='read_student')

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
        model_1 = self.bc.database.create(profile_academy=True,
                                          profile_academy_kwargs=profile_academy_kwargs,
                                          models=base)

        model_2 = self.bc.database.create(profile_academy=True,
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
            'address': model_1['profile_academy'].address,
            'created_at': self.datetime_to_iso(model_1['profile_academy'].created_at),
            'email': model_1['profile_academy'].email,
            'first_name': model_1['profile_academy'].first_name,
            'id': model_1['profile_academy'].id,
            'last_name': model_1['profile_academy'].last_name,
            'phone': model_1['profile_academy'].phone,
            'role': {
                'id': 'student',
                'name': 'student',
                'slug': 'student'
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
        self.assertEqual(self.all_profile_academy_dict(), [{
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

    """
    🔽🔽🔽 GET query status
    """

    def test_academy_student__query_status__bad_status(self):
        base = self.bc.database.create(user=1, role='student', capability='read_student')
        for status in PROFILE_ACADEMY_STATUS:
            bad_status = [x for x in PROFILE_ACADEMY_STATUS if status != x][0]
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_student') + f'?status={bad_status}'
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                             self.bc.format.to_dict(model.profile_academy))

            self.bc.database.delete('authenticate.ProfileAcademy')

    def test_academy_student__query_status__one_status__uppercase(self):
        base = self.bc.database.create(user=1, role='student', capability='read_student')
        for status in PROFILE_ACADEMY_STATUS:
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_student') + f'?status={status.upper()}'
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

    def test_academy_student__query_status__one_status__lowercase(self):
        base = self.bc.database.create(user=1, role='student', capability='read_student')
        for status in PROFILE_ACADEMY_STATUS:
            profile_academy = {'status': status}

            model = self.bc.database.create(profile_academy=(2, profile_academy), models=base)
            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_student') + f'?status={status.lower()}'
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
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_academy_student__spy_extensions(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_student',
                                        profile_academy=True)

        url = reverse_lazy('authenticate:academy_student')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension']),
        ])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_academy_student__spy_extension_arguments(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'konan'
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='read_student',
                                        profile_academy=True)

        url = reverse_lazy('authenticate:academy_student')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(paginate=True),
        ])


class StudentPostTestSuite(AuthTestCase):
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__no_user__invite_is_false(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_student')
        data = {'role': role, 'invite': False}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'user-not-found', 'status_code': 400}

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

        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__no_invite(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_student')
        data = {'role': role, 'invite': True}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'no-email-or-id', 'status_code': 400}

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

        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__exists_profile_academy_with_this_email__is_none(self):
        """Test /academy/:id/member"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        profile_academy = {'email': None}
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=profile_academy)
        url = reverse_lazy('authenticate:academy_student')

        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': model.profile_academy.email,
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'already-exists-with-this-email', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [self.bc.format.to_dict(model.profile_academy)])

        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__exists_profile_academy_with_this_email__with_email(self):
        """Test /academy/:id/member"""
        role = 'student'
        self.bc.request.set_headers(academy=1)
        profile_academy = {'email': 'dude@dude.dude'}
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=profile_academy)
        url = reverse_lazy('authenticate:academy_student')

        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': model.profile_academy.email,
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'already-exists-with-this-email', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [self.bc.format.to_dict(model.profile_academy)])

        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__user_with_not_student_role(self):
        """Test /academy/:id/member"""
        role = 'konan'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=True)
        url = reverse_lazy('authenticate:academy_student')
        data = {'role': role, 'user': model['user'].id, 'first_name': 'Kenny', 'last_name': 'McKornick'}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'already-exists', 'status_code': 400}

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

        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 Without Role student
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('random.getrandbits', MagicMock(side_effect=getrandbits))
    def test_academy_student__post__without_role_student(self):
        """Test /academy/:id/member"""

        role = 'hitman'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'role-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 POST with Cohort in body
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('random.getrandbits', MagicMock(side_effect=getrandbits))
    def test_academy_student__post__with_cohort_in_body(self):
        """Test /academy/:id/member"""

        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        skip_cohort=True,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
            'cohort': 1,
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'cohort-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 POST data with user but not found
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('random.getrandbits', MagicMock(side_effect=getrandbits))
    def test_academy_student__post__with_user_but_not_found(self):
        """Test /academy/:id/member"""

        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
            'user': 2,
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'user-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 POST data with User and Cohort in body
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('random.getrandbits', MagicMock(side_effect=getrandbits))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_academy_student__post__with_user_and_cohort_in_data(self):
        """Test /academy/:id/member"""

        roles = [{'name': 'konan', 'slug': 'konan'}, {'name': 'student', 'slug': 'student'}]
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(role=roles,
                                        user=2,
                                        cohort=1,
                                        capability='crud_student',
                                        profile_academy=1)

        self.bc.request.authenticate(model.user[0])
        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
            'user': 2,
            'cohort': 1,
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'address': None,
            'email': model.user[1].email,
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'phone': '',
            'status': 'INVITED',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy), {
                'academy_id': 1,
                'address': None,
                'email': model.user[1].email,
                'first_name': 'Kenny',
                'id': 2,
                'last_name': 'McKornick',
                'phone': '',
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': 2,
            }
        ])

        token = self.bc.database.get('authenticate.Token', 1, dict=False)
        querystr = urllib.parse.urlencode({'callback': os.getenv('APP_URL', ''), 'token': token})
        url = os.getenv('API_URL') + '/v1/auth/academy/html/invite?' + querystr

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [
            call(
                'academy_invite', model.user[1].email, {
                    'subject':
                    f'Invitation to study at {model.academy.name}',
                    'invites': [{
                        'id': 2,
                        'academy': {
                            'id': 1,
                            'name': model.academy.name,
                            'slug': model.academy.slug,
                            'timezone': None
                        },
                        'role': 'student',
                        'created_at': UTC_NOW
                    }],
                    'user': {
                        'id': 2,
                        'email': model.user[1].email,
                        'first_name': model.user[1].first_name,
                        'last_name': model.user[1].last_name,
                        'github': None,
                        'profile': None
                    },
                    'LINK':
                    url,
                }),
        ])

    """
    🔽🔽🔽 POST data without user
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('random.getrandbits', MagicMock(side_effect=getrandbits))
    def test_academy_student__post__without_user_in_data(self):
        """Test /academy/:id/member"""

        role = 'student'
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'address': None,
            'email': 'dude@dude.dude',
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'phone': '',
            'status': 'INVITED',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy), {
                'academy_id': 1,
                'address': None,
                'email': 'dude@dude.dude',
                'first_name': 'Kenny',
                'id': 2,
                'last_name': 'McKornick',
                'phone': '',
                'role_id': 'student',
                'status': 'INVITED',
                'user_id': None,
            }
        ])

        invite = self.bc.database.get('authenticate.UserInvite', 1, dict=False)
        params = {'callback': ''}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
            str(TOKEN) + '?' + querystr

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            generate_user_invite({
                'id': 1,
                'academy_id': 1,
                'author_id': 1,
                'email': 'dude@dude.dude',
                'first_name': 'Kenny',
                'last_name': 'McKornick',
                'role_id': 'student',
                'token': TOKEN,
            }),
        ])
        self.assertEqual(actions.send_email_message.call_args_list, [
            call('welcome', 'dude@dude.dude', {
                'email': 'dude@dude.dude',
                'subject': 'Welcome to 4Geeks.com',
                'LINK': url,
                'FIST_NAME': 'Kenny'
            })
        ])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__without_user_in_data__invite_already_exists(self):
        """Test /academy/:id/member"""

        role = 'student'
        self.bc.request.set_headers(academy=1)
        user = {'email': 'dude@dude.dude'}
        user_invite = {'email': 'dude2@dude.dude'}
        model = self.bc.database.create(authenticate=True,
                                        user=user,
                                        user_invite=user_invite,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude2@dude.dude',
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'already-invited', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

        invite = self.bc.database.get('authenticate.UserInvite', 1, dict=False)
        params = {'callback': ''}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
            str(TOKEN) + '?' + querystr

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_academy_student__post__without_user_in_data__user_already_exists(self):
        """Test /academy/:id/member"""

        role = 'student'
        self.bc.request.set_headers(academy=1)
        user = {'email': 'dude@dude.dude'}
        model = self.bc.database.create(authenticate=True,
                                        user=user,
                                        user_invite=user,
                                        role=role,
                                        capability='crud_student',
                                        profile_academy=1)

        url = reverse_lazy('authenticate:academy_student')
        data = {
            'first_name': 'Kenny',
            'last_name': 'McKornick',
            'invite': True,
            'email': 'dude@dude.dude',
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'already-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

        invite = self.bc.database.get('authenticate.UserInvite', 1, dict=False)
        params = {'callback': ''}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
            str(TOKEN) + '?' + querystr

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(actions.send_email_message.call_args_list, [])


class StudentDeleteTestSuite(AuthTestCase):
    def test_academy_student_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_header(self):
        """Test /cohort/:id/user without auth"""
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'Missing academy_id parameter expected for the endpoint url or \'Academy\' header',
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_capability(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_student for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='crud_student',
                                        role='student')
        url = reverse_lazy('authenticate:academy_student')
        response = self.client.delete(url)
        json = response.json()
        expected = {'details': 'Missing user_id or academy_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_profile_academy_dict(), [{
            **self.model_to_dict(model, 'profile_academy'),
        }])

    def test_academy_student_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_student', role='student')

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

            url = (reverse_lazy('authenticate:academy_student') + f'?{field}=' +
                   str(getattr(model['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_student', role='student')

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

            url = (reverse_lazy('authenticate:academy_student') + f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [])

    def test_academy_student_delete_in_bulk_with_two_but_is_not_student(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_student', role='hitman')

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

            url = (reverse_lazy('authenticate:academy_student') + f'?{field}=' +
                   str(getattr(model1['profile_academy'], field)) + ',' +
                   str(getattr(model2['profile_academy'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_profile_academy_dict(), [{
                **self.model_to_dict(model1, 'profile_academy'),
            }, {
                **self.model_to_dict(model2, 'profile_academy'),
            }])

            for model in ProfileAcademy.objects.all():
                model.delete()
