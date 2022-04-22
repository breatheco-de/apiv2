"""
This file just can contains duck tests refert to AcademyInviteView
"""
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from rest_framework import status
from rest_framework.response import Response

from breathecode.utils import capable_of


@capable_of('invite_resend')
def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


# Duck test
class MemberGetDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_duck_test__without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duck_test__without_capabilities(self):
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_invite for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_duck_test__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='read_invite',
                                            role='role',
                                            profile_academy=1)

            url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
            response = self.client.get(url)

            json = response.json()
            expected = {'detail': 'user-invite-not-found', 'status_code': 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.AcademyInviteView.get', MagicMock(side_effect=view_method_mock))
    def test_duck_test__with_auth___mock_view(self):
        model = self.bc.database.create(academy=3,
                                        capability='invite_resend',
                                        role='role',
                                        profile_academy=[{
                                            'academy_id': id
                                        } for id in range(1, 4)])

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': n})
            response = self.client.get(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': '1', 'invite_id': n}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# Duck test
class MemberPutDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_id_member_id__without_capabilities(self):
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: invite_resend for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_member_id__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='invite_resend',
                                            role='role',
                                            profile_academy=1)

            url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': 1})
            response = self.client.put(url)

            json = response.json()
            expected = {'detail': 'user-invite-not-found', 'status_code': 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.AcademyInviteView.put', MagicMock(side_effect=view_method_mock))
    def test_academy_id_member_id__with_auth___mock_view(self):
        model = self.bc.database.create(academy=3,
                                        capability='invite_resend',
                                        role='role',
                                        profile_academy=[{
                                            'academy_id': id
                                        } for id in range(1, 4)])

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy('authenticate:academy_invite_id', kwargs={'invite_id': n})
            response = self.client.put(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': '1', 'invite_id': n}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
