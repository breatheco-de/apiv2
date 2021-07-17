"""
Test cases for /academy/user/me/invite && academy/user/invite
"""
from breathecode.authenticate.models import ProfileAcademy
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    def test_invite_change_status_without_auth(self):
        """Test /academy/user/invite without auth"""
        url = reverse_lazy('authenticate:user_invite')

        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invite_change_status_wrong_academy(self):
        self.headers(academy=1)
        url = reverse_lazy('authenticate:user_invite')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invite_change_status_without_capability(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, )
        url = reverse_lazy('authenticate:user_invite')
        response = self.client.delete(url)
        json = response.json()
        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: crud_invite for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_change_status_without_passing_ids(self):
        """Test academy/user/me/invite"""
        self.headers(academy=1)

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }

        slug = 'missing_ids'

        model = self.generate_models(academy=True,
                                     capability='crud_invite',
                                     authenticate=True,
                                     role='potato',
                                     invite_kwargs=invite_kwargs,
                                     profile_academy=True)

        url = reverse_lazy('authenticate:user_me_invite')

        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], slug)
        self.assertEqual(self.all_user_invite_dict(), [])

    def test_invite_change_status_to_accepted_in_bulk_with_ids(self):
        """Test academy/user/me/invite"""
        self.headers(academy=1)
        base = self.generate_models(academy=True,
                                    capability='crud_invite',
                                    authenticate=True,
                                    role='potato',
                                    user_kwargs={'email': 'a@a.com'})

        invite_kwargs = {
            'status': 'ACCEPTED',
            'email': 'a@a.com',
            'id': 1,
        }

        model1 = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      user_invite=True,
                                      user_invite_kwargs=invite_kwargs,
                                      models=base)
        invite_kwargs['id'] = 2

        model2 = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      user_invite=True,
                                      user_invite_kwargs=invite_kwargs,
                                      models=base)

        url = reverse_lazy('authenticate:user_me_invite') + '?id=1,2'
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{
            'created_at':
            self.datetime_to_iso(model1['user_invite'].created_at),
            'email':
            'a@a.com',
            'first_name':
            None,
            'id':
            1,
            'invite_url':
            f"http://localhost:8000/v1/auth/member/invite/{model1['user_invite'].token}",
            'last_name':
            None,
            'sent_at':
            None,
            'status':
            'ACCEPTED',
            'token':
            model1['user_invite'].token
        }, {
            'created_at':
            self.datetime_to_iso(model2['user_invite'].created_at),
            'email':
            'a@a.com',
            'first_name':
            None,
            'id':
            2,
            'invite_url':
            f"http://localhost:8000/v1/auth/member/invite/{model2['user_invite'].token}",
            'last_name':
            None,
            'sent_at':
            None,
            'status':
            'ACCEPTED',
            'token':
            model2['user_invite'].token
        }])
        self.assertEqual(self.all_user_invite_dict(),
                         [{
                             'academy_id': 1,
                             'author_id': 1,
                             'cohort_id': 1,
                             'email': 'a@a.com',
                             'first_name': None,
                             'id': 1,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'potato',
                             'sent_at': None,
                             'status': 'ACCEPTED',
                             'token': model1['user_invite'].token
                         }, {
                             'academy_id': 1,
                             'author_id': 1,
                             'cohort_id': 2,
                             'email': 'a@a.com',
                             'first_name': None,
                             'id': 2,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'potato',
                             'sent_at': None,
                             'status': 'ACCEPTED',
                             'token': model2['user_invite'].token
                         }])

    def test_invite_change_status_to_accepted_invitations_not_matched(self):
        """Test academy/user/me/invite"""
        self.headers(academy=1)

        base = self.generate_models(academy=True,
                                    capability='crud_invite',
                                    authenticate=True,
                                    role='potato',
                                    user_kwards={'email': 'a@a.com'})

        invite_kwargs = {'status': 'ACCEPTED', 'email': 'a@a.com'}

        model1 = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      user_invite=True,
                                      user_invite_kwargs=invite_kwargs,
                                      models=base)

        model2 = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      user_invite=True,
                                      user_invite_kwargs=invite_kwargs,
                                      models=base)

        url = reverse_lazy('authenticate:user_me_invite') + '?id=1,2'
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
