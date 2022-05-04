"""
Test cases for /academy/user/me/invite && academy/user/invite
"""
from breathecode.authenticate.models import ProfileAcademy
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from ..mixins.new_auth_test_case import AuthTestCase

STATUSES = [
    'PENDING',
    'REJECTED',
    'ACCEPTED',
    'WAITING_LIST',
]


def generate_user_invite(self, model, user_invite, arguments={}):
    return {
        'academy': {
            'id': model.academy.id,
            'name': model.academy.name,
            'slug': model.academy.slug,
        },
        'cohort': {
            'name': model.cohort.name,
            'slug': model.cohort.slug,
        },
        'created_at': self.bc.datetime.to_iso_string(user_invite.created_at),
        'email': user_invite.email,
        'first_name': user_invite.first_name,
        'id': user_invite.id,
        'invite_url': f'http://localhost:8000/v1/auth/member/invite/{user_invite.token}',
        'last_name': user_invite.last_name,
        'role': {
            'id': model.role.slug,
            'name': model.role.name,
            'slug': model.role.slug,
        },
        'sent_at': user_invite.sent_at,
        'status': user_invite.status,
        'token': user_invite.token,
        **arguments,
    }


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """
    def test_academy_user_invite__without_auth(self):
        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_user_invite__wrong_academy(self):
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET auth capability
    """

    def test_academy_user_invite__get__without_capability(self):
        model = self.generate_models(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_invite for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without UserInvite
    """

    def test_academy_user_invite__get__without_data(self):
        model = self.generate_models(user=1, profile_academy=1, role=1, capability='read_invite')

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with two UserInvite with status PENDING
    """

    def test_academy_user_invite__get__with_two_user_invite__status_invite(self):
        user_invite = {'status': 'PENDING'}
        model = self.generate_models(user=1,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_invite',
                                     user_invite=(2, user_invite))

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.get(url)

        json = response.json()
        expected = [
            generate_user_invite(self, model, user_invite) for user_invite in reversed(model.user_invite)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         self.bc.format.to_dict(model.user_invite))

    """
    🔽🔽🔽 GET with two UserInvite with statuses will be ignored
    """

    def test_academy_user_invite__get__with_two_user_invite__statuses_will_be_ignored(self):
        statuses_will_be_ignored = [x for x in STATUSES if x != 'PENDING']
        for x in statuses_will_be_ignored:
            user_invite = {'status': x}
            model = self.generate_models(user=1,
                                         profile_academy=1,
                                         role=1,
                                         capability='read_invite',
                                         user_invite=(2, user_invite))

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_user_invite')
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                             self.bc.format.to_dict(model.user_invite))

            # teardown
            self.bc.database.delete('authenticate.UserInvite')

    """
    🔽🔽🔽 GET with two UserInvite passing one status
    """

    def test_academy_user_invite__get__with_two_user_invite__passing_one_status(self):
        for x in STATUSES:
            user_invite = {'status': x}
            model = self.generate_models(user=1,
                                         profile_academy=1,
                                         role=1,
                                         capability='read_invite',
                                         user_invite=(2, user_invite))

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_user_invite') + f'?status={x}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                generate_user_invite(self, model, user_invite, arguments={'status': x})
                for user_invite in reversed(model.user_invite)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                             self.bc.format.to_dict(model.user_invite))

            # teardown
            self.bc.database.delete('authenticate.UserInvite')

    """
    🔽🔽🔽 GET with two UserInvite passing two statuses
    """

    def test_academy_user_invite__get__with_two_user_invite__passing_two_statuses(self):
        for n in range(0, 4):
            current = n

            # is possible bin function return a string start with 'b'
            binary = ''.join(bin(n + 1)[-2:].split('b'))

            # 4 = '100', it take '00' = 0
            next = int(binary, 2)

            first_status = STATUSES[current]
            second_status = STATUSES[next]
            user_invites = [{'status': first_status}, {'status': second_status}]
            model = self.generate_models(user=1,
                                         profile_academy=1,
                                         role=1,
                                         capability='read_invite',
                                         user_invite=user_invites)

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_user_invite') + f'?status={first_status},{second_status}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                generate_user_invite(
                    self,
                    model,
                    user_invite,
                    arguments={'status': first_status if user_invite.id % 2 == 1 else second_status})
                for user_invite in reversed(model.user_invite)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                             self.bc.format.to_dict(model.user_invite))

            # teardown
            self.bc.database.delete('authenticate.UserInvite')

    """
    🔽🔽🔽 DELETE auth capability
    """

    def test_academy_user_invite__delete__without_capability(self):
        model = self.generate_models(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite')
        response = self.client.delete(url)
        json = response.json()
        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_invite for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 DELETE providing two id in the params and two UserInvite
    """

    def test_academy_user_invite__delete__in_bulk_with_two_invites(self):
        user_invites = [{'email': choice(['a@a.com', 'b@b.com', 'c@c.com'])} for _ in range(0, 2)]
        model = self.generate_models(academy=1,
                                     capability='crud_invite',
                                     role=1,
                                     user=1,
                                     profile_academy=1,
                                     user_invite=user_invites)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite') + '?id=1,2'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 DELETE not providing the id param and one UserInvite
    """

    def test_academy_user_invite__delete__without_passing_ids(self):

        invite_kwargs = {'email': choice(['a@a.com', 'b@b.com', 'c@c.com'])}
        model = self.generate_models(academy=1,
                                     capability='crud_invite',
                                     user=1,
                                     role='potato',
                                     user_invite=invite_kwargs,
                                     profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite')

        response = self.client.delete(url)
        json = response.json()

        self.bc.check.partial_equality(json, {'detail': 'missing_ids'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

    """
    🔽🔽🔽 DELETE providing the id param and one UserInvite but from another academy
    """

    def test_academy_user_invite__delete__passing_ids__deleting_invite_of_another_academy(self):

        invite_kwargs = {'email': choice(['a@a.com', 'b@b.com', 'c@c.com']), 'academy_id': 2}
        model = self.generate_models(academy=2,
                                     capability='crud_invite',
                                     user=1,
                                     role='potato',
                                     user_invite=invite_kwargs,
                                     profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('authenticate:academy_user_invite') + '?id=1'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])
