"""
Test /v1/auth/subscribe
"""
import hashlib
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase

now = timezone.now()


class SubscribeTestSuite(AuthTestCase):
    """Test /v1/auth/subscribe"""
    """
    🔽🔽🔽 Post without email
    """
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__without_email(self):
        url = reverse_lazy('authenticate:subscribe')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'without-email', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 Post without UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__without_user_invite(self):
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123'
        }
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'id': 1, **data}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             'academy_id': None,
                             'author_id': None,
                             'cohort_id': None,
                             'id': 1,
                             'role_id': None,
                             'sent_at': None,
                             'status': 'WAITING_LIST',
                             'token': hashlib.sha1(
                                 (str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                             **data,
                         }])

    """
    🔽🔽🔽 Post with UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'pokemon@potato.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'user-invite-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

    """
    🔽🔽🔽 Post with UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__user_exists(self):
        """
        Descriptions of models are being generated:

          User(id=1):
            groups: []
            user_permissions: []
        """

        user = {'email': 'pokemon@potato.io'}
        model = self.bc.database.create(user=user)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'user-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 Post with UserInvite with other email
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'henrrieta@horseman.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123'
        }
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'id': 2, **data}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite), {
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 2,
                'role_id': None,
                'sent_at': None,
                'status': 'WAITING_LIST',
                'token': hashlib.sha1((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                **data,
            }
        ])
