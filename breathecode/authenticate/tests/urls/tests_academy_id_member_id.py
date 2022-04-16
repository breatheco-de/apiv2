"""
Test cases for /academy/:id/member/:id
"""
from unittest.mock import MagicMock, patch
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.response import Response

from breathecode.utils import capable_of
from ..mixins.new_auth_test_case import AuthTestCase


@capable_of('read_member')
def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


# Duck test
class MemberGetDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
        response = self.client.get(url)
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
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_member for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_member_id__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='read_member',
                                            role='role',
                                            profile_academy=1)
            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': f'{n}'
                               })
            response = self.client.get(url)
            json = response.json()

            self.bc.check.partial_equality(json, {'academy': {'id': n}})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.get', MagicMock(side_effect=view_method_mock))
    def test_academy_id_member_id__with_auth___mock_view(self):
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=[{
                                            'academy_id': id
                                        } for id in range(1, 4)])

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': f'{n}'
                               })
            response = self.client.get(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': n, 'user_id_or_email': f'{n}'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# Duck test
class MemberPutDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
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
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_member for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_member_id__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='crud_member',
                                            role='role',
                                            profile_academy=1)

            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': '1'
                               })
            response = self.client.put(url)

            json = response.json()
            expected = {'role': ['This field is required.']}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.put', MagicMock(side_effect=view_method_mock))
    def test_academy_id_member_id__with_auth___mock_view(self):
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=[{
                                            'academy_id': id
                                        } for id in range(1, 4)])

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': f'{n}'
                               })
            response = self.client.put(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': n, 'user_id_or_email': f'{n}'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# Duck test
class MemberDeleteDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
        response = self.client.delete(url)
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
        url = reverse_lazy('authenticate:academy_id_member_id',
                           kwargs={
                               'academy_id': 1,
                               'user_id_or_email': '1'
                           })
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_member for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_member_id__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='crud_member',
                                            role='role',
                                            profile_academy=1)

            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': f'{n}'
                               })
            response = self.client.delete(url)
            expected = b''

            self.assertEqual(response.content, expected)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.MemberView.delete', MagicMock(side_effect=view_method_mock))
    def test_academy_id_member_id__with_auth___mock_view(self):
        model = self.bc.database.create(academy=3,
                                        capability='read_member',
                                        role='role',
                                        profile_academy=[{
                                            'academy_id': id
                                        } for id in range(1, 4)])

        for n in range(1, 4):
            self.bc.request.authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy('authenticate:academy_id_member_id',
                               kwargs={
                                   'academy_id': n,
                                   'user_id_or_email': f'{n}'
                               })
            response = self.client.delete(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': n, 'user_id_or_email': f'{n}'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
