"""
This file contains test over AcademyInviteView, if it change, the duck tests will deleted
"""
import os
import re
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from rest_framework import status
from rest_framework.response import Response

from breathecode.utils import capable_of
from breathecode.tests.mocks import apply_requests_post_mock

from datetime import timedelta
from django.utils import timezone


@capable_of('invite_resend')
def view_method_mock(request, *args, **kwargs):
    response = {'args': args, 'kwargs': kwargs}
    return Response(response, status=200)


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


# Duck test
class MemberGetDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """
    def test_duck_test__without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
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
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
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

            url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
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

            url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': n})
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
    def test_duck_test__without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
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
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: invite_resend for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_duck_test__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True,
                                            capability='invite_resend',
                                            role='role',
                                            profile_academy=1)

            url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
            response = self.client.put(url)

            json = response.json()
            expected = {'detail': 'user-invite-not-found', 'status_code': 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch('breathecode.authenticate.views.AcademyInviteView.put', MagicMock(side_effect=view_method_mock))
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

            url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': n})
            response = self.client.put(url)
            json = response.json()
            expected = {'args': [], 'kwargs': {'academy_id': '1', 'invite_id': n}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    def test_resend_invite__no_auth(self):
        """Test """
        self.headers(academy=1)
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_resend_invite__no_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, syllabus=True)
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})

        response = self.client.put(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: invite_resend for "
            'academy 1',
            'status_code': 403
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    """
    🔽🔽🔽 GET capability
    """

    def test_resend_invite__get__with_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, syllabus=True)

        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_invite for academy 1",
            'status_code': 403,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test_resend_invite__get__without_data(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_invite',
                                     role='potato',
                                     syllabus=True)

        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'user-invite-not-found', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    """
    🔽🔽🔽 GET with data
    """

    def test_resend_invite__put__with_data(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=1,
                                     capability='read_invite',
                                     role='potato',
                                     user_invite=1,
                                     syllabus=1)

        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = generate_user_invite(self, model, model.user_invite, arguments={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 PUT capability
    """

    def test_resend_invite__put__with_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True)

        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1359})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'user-invite-not-found', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_resend_invite_no_invitation(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='invite_resend',
            #  user_invite=1,
            role='potato',
            syllabus=True)

        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'user-invite-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        all_user_invite = [x for x in self.all_user_invite_dict() if x.pop('sent_at')]
        self.assertEqual(all_user_invite, [])

    @patch('requests.post',
           apply_requests_post_mock([
               (201, f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages", {})
           ]))
    def test_resend_invite_with_invitation(self):
        """Test """
        self.headers(academy=1)
        profile_academy_kwargs = {'email': 'email@dotdotdotdot.dot'}
        user_invite_kwargs = {'email': 'email@dotdotdotdot.dot'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True,
                                     user_invite=True,
                                     profile_academy_kwargs=profile_academy_kwargs,
                                     user_invite_kwargs=user_invite_kwargs)
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
        json = response.json()
        created = json['created_at']
        sent = json['sent_at']
        del json['sent_at']
        del json['created_at']

        expected = {
            'id': 1,
            'status': 'PENDING',
            'email': 'email@dotdotdotdot.dot',
            'first_name': None,
            'last_name': None,
            'token': model.user_invite.token,
            'invite_url': f'http://localhost:8000/v1/auth/member/invite/{model.user_invite.token}',
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            },
            'role': {
                'id': 'potato',
                'name': 'potato',
                'slug': 'potato'
            },
            'cohort': {
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        all_user_invite = [x for x in self.all_user_invite_dict() if x.pop('sent_at')]
        self.assertEqual(all_user_invite, [{
            'id': model['user_invite'].id,
            'email': model['user_invite'].email,
            'academy_id': model['user_invite'].academy_id,
            'cohort_id': model['user_invite'].cohort_id,
            'role_id': model['user_invite'].role_id,
            'first_name': model['user_invite'].first_name,
            'last_name': model['user_invite'].last_name,
            'token': model['user_invite'].token,
            'author_id': model['user_invite'].author_id,
            'status': model['user_invite'].status,
            'phone': model['user_invite'].phone,
        }])

    def test_resend_invite_recently(self):
        """Test """
        self.headers(academy=1)
        past_time = timezone.now() - timedelta(seconds=100)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True,
                                     user_invite=True,
                                     token=True,
                                     user_invite_kwargs={'sent_at': past_time})
        url = reverse_lazy('authenticate:member_invite_resend_id', kwargs={'invite_id': 1})
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'sent-at-diff-less-two-minutes', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.all_user_invite_dict(),
                         [{
                             **self.model_to_dict(model, 'user_invite'),
                             'sent_at': past_time,
                         }])
