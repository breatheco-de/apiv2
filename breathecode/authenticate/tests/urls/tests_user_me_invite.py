"""
Set of tests for MeInviteView, this include duck tests
"""
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from rest_framework.response import Response
from ..mixins.new_auth_test_case import AuthTestCase


def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


def generate_user_invite(self, model, user_invite, arguments={}):
    return {
        'academy': None,
        'cohort': None,
        'created_at': self.bc.datetime.to_iso_string(user_invite.created_at),
        'email': user_invite.email,
        'first_name': user_invite.first_name,
        'id': user_invite.id,
        'invite_url': f'http://localhost:8000/v1/auth/member/invite/{user_invite.token}',
        'last_name': user_invite.last_name,
        'role': user_invite.role,
        'sent_at': user_invite.sent_at,
        'status': user_invite.status,
        'token': user_invite.token,
        **arguments,
    }


# set of duck tests, the tests about decorators are ignorated in the main test file
class MemberSetOfDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 GET check the param is being passed
    """
    @patch('breathecode.authenticate.views.MeInviteView.get', MagicMock(side_effect=view_method_mock))
    def test_duck_test__get__with_auth___mock_view(self):
        model = self.bc.database.create(user=3)

        for n in range(0, 3):
            self.bc.request.authenticate(model.user[n])

            url = reverse_lazy('authenticate:user_me_invite')
            response = self.client.get(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 PUT check the param is being passed
    """

    @patch('breathecode.authenticate.views.MeInviteView.put', MagicMock(side_effect=view_method_mock))
    def test_duck_test__put__with_auth___mock_view(self):
        model = self.bc.database.create(user=3)

        for n in range(0, 3):
            self.bc.request.authenticate(model.user[n])

            url = reverse_lazy('authenticate:user_me_invite')
            response = self.client.put(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticateTestSuite(AuthTestCase):
    def test_user_me_invite__without_auth(self):
        """Test /academy/user/invite without auth"""
        url = reverse_lazy('authenticate:user_me_invite')

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me_invite__wrong_academy(self):
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('authenticate:user_me_invite')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET with 0 UserInvite
    """

    def test_user_me_invite__get__without_user_invites(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:user_me_invite')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET with 1 UserInvite, email not match between User and UserInvite
    """

    def test_user_me_invite__get__with_one_user_invite__email_not_match(self):
        user_invite = {'email': 'eeeeeeee@eeeeeeee.eeeeeeee'}
        model = self.bc.database.create(user=1, user_invite=user_invite)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:user_me_invite')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [self.bc.format.to_dict(model.user_invite)])

    """
    🔽🔽🔽 GET with 1 UserInvite with status INVITED, email match between User and UserInvite
    """

    def test_user_me_invite__get__with_one_user_invite__email_match__status_pending(self):
        user = {'email': 'eeeeeeee@eeeeeeee.eeeeeeee'}
        user_invite = {'email': 'eeeeeeee@eeeeeeee.eeeeeeee', 'status': 'PENDING'}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:user_me_invite')
        response = self.client.get(url)

        json = response.json()
        expected = [generate_user_invite(self, model, model.user_invite)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [self.bc.format.to_dict(model.user_invite)])

    """
    🔽🔽🔽 GET with 3 UserInvite with bad statuses, email match between User and UserInvite
    """

    def test_user_me_invite__get__with_three_user_invite__email_match__bad_statuses(self):
        bad_statuses = ['ACCEPTED', 'REJECTED', 'WAITING_LIST']
        user = {'email': 'eeeeeeee@eeeeeeee.eeeeeeee'}
        user_invites = [{'email': 'eeeeeeee@eeeeeeee.eeeeeeee', 'status': x} for x in bad_statuses]
        model = self.bc.database.create(user=user, user_invite=user_invites)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:user_me_invite')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         self.bc.format.to_dict(model.user_invite))

    """
    🔽🔽🔽 GET with 4 UserInvite with different statuses, email match between User and UserInvite
    """

    def test_user_me_invite__get__with_four_user_invite__email_match__different_statuses(self):
        statuses = ['PENDING', 'ACCEPTED', 'REJECTED', 'WAITING_LIST']
        user = {'email': 'eeeeeeee@eeeeeeee.eeeeeeee'}
        user_invites = [{'email': 'eeeeeeee@eeeeeeee.eeeeeeee', 'status': x} for x in statuses]
        model = self.bc.database.create(user=user, user_invite=user_invites)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:user_me_invite') + f'?status={",".join(statuses)}'
        response = self.client.get(url)

        json = response.json()
        expected = [generate_user_invite(self, model, user_invite) for user_invite in model.user_invite]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         self.bc.format.to_dict(model.user_invite))

    """
    🔽🔽🔽 PUT without new status in the url
    """

    def test_user_me_invite__put__without_passing_ids(self):
        """Test academy/user/me/invite"""
        self.bc.request.set_headers(academy=1)

        invite_kwargs = {
            'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        }

        slug = 'missing-status'

        model = self.generate_models(academy=True,
                                     capability='crud_invite',
                                     authenticate=True,
                                     role='potato',
                                     invite_kwargs=invite_kwargs,
                                     profile_academy=True)

        url = reverse_lazy('authenticate:user_me_invite')

        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], slug)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
