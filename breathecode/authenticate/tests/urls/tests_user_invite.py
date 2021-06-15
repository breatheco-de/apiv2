"""
Test cases for /academy/user/me/invite && academy/user/invite
"""
from breathecode.authenticate.models import ProfileAcademy
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    def test_invite_delete_in_bulk_without_auth(self):
        """Test /academy/user/invite without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:user_invite')

        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invite_delete_in_bulk_with_two_invites(self):
        """Test /academy/user/invite with two invites"""
        self.headers(academy=1)

        base = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato')

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }
        model1 = self.generate_models(authenticate=True, profile_academy=True,
                                      user_invite_kwargs=invite_kwargs, models=base)

        model2 = self.generate_models(authenticate=True, profile_academy=True,
                                      user_invite_kwargs=invite_kwargs, models=base)

        url = reverse_lazy('authenticate:user_invite') + '?id=1,2'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_user_invite_dict(), [])

    def test_invite_delete_without_passing_ids(self):
        """Test /academy/user/invite without invites"""
        self.headers(academy=1)

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }

        slug = "missing_ids"

        model = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato', user_invite_kwargs=invite_kwargs, profile_academy=True)

        url = reverse_lazy('authenticate:user_invite')

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], slug)
        self.assertEqual(self.all_user_invite_dict(), [])
