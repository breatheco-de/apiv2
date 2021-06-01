"""
Test cases for /academy/user/invite
"""
from breathecode.authenticate.models import ProfileAcademy
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    def test_invite_delete_in_bulk_with_two(self):
        """Test /academy/user/invite with two"""
        self.headers(academy=1)

        base = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato')

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }
        model1 = self.generate_models(authenticate=True, profile_academy=True,
                                      invite_kwargs=invite_kwargs, models=base)

        model2 = self.generate_models(authenticate=True, profile_academy=True,
                                      invite_kwargs=invite_kwargs, models=base)

        url = (reverse_lazy('authenticate:user_invite') + '?id=1,2')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_user_invite_dict(), [])

    def test_invite_delete_without_ids(self):
        """Test /academy/user/invite without ids"""
        self.headers(academy=1)

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }

        model = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato', invite_kwargs=invite_kwargs, profile_academy=True)

        url = (reverse_lazy('authenticate:user_invite') + "")

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_user_invite_dict(), [])

    def test_invite_change_status_without_passing_ids(self):
        """Test academy/user/me/invite"""
        self.headers(academy=1)

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }

        model = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato', invite_kwargs=invite_kwargs, profile_academy=True)

        url = (reverse_lazy('authenticate:user_me_invite') + "")

        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_user_invite_dict(), [])

    def test_invite_change_status(self):
        """Test academy/user/me/invite"""
        self.headers(academy=1)

        base = self.generate_models(
            academy=True, capability='read_invite', authenticate=True, role='potato')

        invite_kwargs = {
            'status': "ACCEPTED",
        }

        model1 = self.generate_models(authenticate=True, profile_academy=True,
                                      invite_kwargs=invite_kwargs, models=base)

        model2 = self.generate_models(authenticate=True, profile_academy=True,
                                      invite_kwargs=invite_kwargs, models=base)

        url = (reverse_lazy('authenticate:user_me_invite') + '?id=1,2')
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_user_invite_dict(), [])
