"""
Set of tests for MeInviteView, this include duck tests
"""
from unittest.mock import MagicMock, PropertyMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice
from rest_framework.response import Response
from ..mixins.new_auth_test_case import AuthTestCase


def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


# set of duck tests, the tests about decorators are ignorated in the main test file
class MemberSetOfDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 GET check the param is being passed
    """

    @patch('breathecode.authenticate.views.MeInviteView.get', MagicMock(side_effect=view_method_mock))
    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_duck_test__get__with_auth___mock_view(self):
        model = self.bc.database.create(user=3)

        for n in range(0, 3):
            self.bc.request.authenticate(model.user[n])

            url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'accepted'})
            response = self.client.get(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'new_status': 'accepted'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 PUT check the param is being passed
    """

    @patch('breathecode.authenticate.views.MeInviteView.put', MagicMock(side_effect=view_method_mock))
    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_duck_test__put__with_auth___mock_view(self):
        model = self.bc.database.create(user=3)

        for n in range(0, 3):
            self.bc.request.authenticate(model.user[n])

            url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'accepted'})
            response = self.client.put(url)

            json = response.json()
            expected = {'args': [], 'kwargs': {'new_status': 'accepted'}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__without_auth(self):
        """Test /academy/user/invite without auth"""
        url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'pending'})

        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__wrong_academy(self):
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'pending'})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 PUT passing status is not allowed or invalid through of the url
    """

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__passing_invalid_status(self):
        """Test academy/user/me/invite"""
        self.bc.request.set_headers(academy=1)

        statuses_upper = ['WAITING_LIST', 'PENDING']
        statuses_lower = [x.lower() for x in statuses_upper]
        statuses = statuses_upper + statuses_lower

        model = self.generate_models(academy=True,
                                     capability='crud_invite',
                                     authenticate=True,
                                     role='potato',
                                     profile_academy=True)

        for x in statuses:
            url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': x})

            response = self.client.put(url)
            json = response.json()
            expected = {'detail': 'invalid-status', 'status_code': 400}

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(json, expected)
            self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 PUT passing valid statuses through of the url
    """

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__passing_valid_status__without_bulk_mode(self):
        """Test academy/user/me/invite"""
        self.bc.request.set_headers(academy=1)

        statuses_upper = ['ACCEPTED', 'REJECTED']
        statuses_lower = [x.lower() for x in statuses_upper]
        statuses = statuses_upper + statuses_lower

        model = self.generate_models(academy=True,
                                     capability='crud_invite',
                                     authenticate=True,
                                     role='potato',
                                     profile_academy=True)

        for x in statuses:
            url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': x})

            response = self.client.put(url)
            json = response.json()
            expected = {'detail': 'missing-ids', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 PUT bulk mode
    """

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__to_accepted_in_bulk_with_ids(self):
        """Test academy/user/me/invite"""
        self.bc.request.set_headers(academy=1)
        base = self.generate_models(academy=True,
                                    capability='crud_invite',
                                    authenticate=True,
                                    role='potato',
                                    skip_cohort=True,
                                    user_kwargs={'email': 'a@a.com'})

        invite_kwargs = {
            'status': 'PENDING',
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

        url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'accepted'
                                                                         }) + '?id=1,2'
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             'user_id': 1,
                             'academy_id': 1,
                             'author_id': 1,
                             'cohort_id': 1,
                             'email': 'a@a.com',
                             'first_name': None,
                             'conversion_info': None,
                             'has_marketing_consent': False,
                             'event_slug': None,
                             'asset_slug': None,
                             'id': 1,
                             'is_email_validated': False,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'potato',
                             'sent_at': None,
                             'status': 'ACCEPTED',
                             'token': model1['user_invite'].token,
                             'process_message': '',
                             'process_status': 'PENDING',
                             'syllabus_id': None,
                             'city': None,
                             'country': None,
                             'latitude': None,
                             'longitude': None,
                             'email_quality': None,
                             'email_status': None,
                         }, {
                             'user_id': 1,
                             'academy_id': 1,
                             'author_id': 1,
                             'cohort_id': 2,
                             'email': 'a@a.com',
                             'first_name': None,
                             'conversion_info': None,
                             'has_marketing_consent': False,
                             'event_slug': None,
                             'asset_slug': None,
                             'id': 2,
                             'is_email_validated': False,
                             'last_name': None,
                             'phone': '',
                             'role_id': 'potato',
                             'sent_at': None,
                             'status': 'ACCEPTED',
                             'token': model2['user_invite'].token,
                             'process_message': '',
                             'process_status': 'PENDING',
                             'syllabus_id': None,
                             'city': None,
                             'country': None,
                             'latitude': None,
                             'longitude': None,
                             'email_quality': None,
                             'email_status': None,
                         }])

    @patch('breathecode.authenticate.signals.invite_status_updated.send', MagicMock())
    def test_user_me_invite_status__to_accepted_invitations_not_matched(self):
        """Test academy/user/me/invite"""
        self.bc.request.set_headers(academy=1)

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

        url = reverse_lazy('authenticate:user_me_invite_status', kwargs={'new_status': 'accepted'
                                                                         }) + '?id=1,2'
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
