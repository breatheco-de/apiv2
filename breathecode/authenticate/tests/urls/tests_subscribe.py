"""
Test /v1/auth/subscribe
"""
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase


class SubscribeTestSuite(AuthTestCase):
    """Test /v1/auth/subscribe"""
    """
    🔽🔽🔽 Post without email
    """
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

    def test_task__post__without_user_invite(self):
        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'id': 1, 'email': 'pokemon@potato.io'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [{
            'academy_id': None,
            'author_id': None,
            'cohort_id': None,
            'email': 'pokemon@potato.io',
            'first_name': None,
            'id': 1,
            'last_name': None,
            'phone': '',
            'role_id': None,
            'sent_at': None,
            'status': 'WAITING_LIST',
            'token': ''
        }])

    """
    🔽🔽🔽 Post with UserInvite
    """

    def test_task__post__with_user_invite__already_exists(self):
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
