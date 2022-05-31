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


# Duck test
class MemberPutDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_duck_test__without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_user_me_invite_status', kwargs={'new_status': 'pending'})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duck_test__with_auth(self):
        model = self.bc.database.create(authenticate=True)

        url = reverse_lazy('authenticate:academy_user_me_invite_status', kwargs={'new_status': 'pending'})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'invalid-status', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.MeInviteView.put', MagicMock(side_effect=view_method_mock))
    def test_duck_test__with_auth___mock_view(self):
        statuses = [
            'pending',
            'rejected',
            'accepted',
            'waiting_list',
        ]
        model = self.bc.database.create(user=1)

        for x in statuses:
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('authenticate:academy_user_me_invite_status', kwargs={'new_status': x})
            response = self.client.put(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'new_status': x}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
