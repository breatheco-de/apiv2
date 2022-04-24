import os
import breathecode.notify.actions as actions
from unittest.mock import MagicMock, patch, call
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mocks.requests import apply_requests_post_mock
from ..mixins.new_auth_test_case import AuthTestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta


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


def generate_profile_academy(self, model, profile_academy, arguments={}):
    return {
        'academy': {
            'id': model.academy.id,
            'name': model.academy.name,
            'slug': model.academy.slug,
        },
        'address': profile_academy.address,
        'created_at': self.bc.datetime.to_iso_string(profile_academy.created_at),
        'email': profile_academy.email,
        'phone': profile_academy.phone,
        'first_name': profile_academy.first_name,
        'id': profile_academy.id,
        'invite_url': 'http://localhost:8000/v1/auth/academy/html/invite',
        'last_name': profile_academy.last_name,
        'role': {
            'id': model.role.slug,
            'name': model.role.name,
            'slug': model.role.slug,
        },
        'user': {
            'email': model.user.email,
            'first_name': model.user.first_name,
            'github': None,
            'id': model.user.id,
            'last_name': model.user.last_name,
            'profile': None,
        },
        'status': profile_academy.status,
        **arguments,
    }


def generate_send_email_message(self, model):
    email = None

    if 'profile_academy' in model:
        email = model.profile_academy.user.email

    elif 'user_invite' in model:
        email = model.user_invite.email

    return [
        call(
            'academy_invite', email, {
                'subject':
                f'Invitation to study at {model.academy.name}',
                'invites': [{
                    'id': model.profile_academy.id,
                    'academy': {
                        'id': model.academy.id,
                        'name': model.academy.name,
                        'slug': model.academy.slug,
                        'timezone': model.academy.timezone,
                    },
                    'role': model.role.slug,
                    'created_at': model.profile_academy.created_at,
                }],
                'user': {
                    'id': model.user.id,
                    'email': model.user.email,
                    'first_name': model.user.first_name,
                    'last_name': model.user.last_name,
                    'github': None,
                    'profile': None
                },
                'LINK':
                'http://localhost:8000/v1/auth/academy/html/invite',
            }),
    ]


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    def test_resend_invite__no_auth(self):
        """Test """
        self.headers(academy=1)
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_resend_invite__no_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, syllabus=True)
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})

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

        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_invite for academy 1",
            'status_code': 403,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET ProfileAcademy and zero UserInvite not found
    """

    def test_resend_invite__get__profile_academy_and_user_invite_not_found(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_invite',
                                     role='potato',
                                     syllabus=True)

        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 2})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    """
    🔽🔽🔽 GET ProfileAcademy with status ACTIVE and without UserInvite
    """

    def test_resend_invite__get__profile_academy_with_status_active(self):
        """Test """
        self.headers(academy=1)
        profile_academy = {'status': 'ACTIVE'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=profile_academy,
                                     capability='read_invite',
                                     role=1,
                                     syllabus=1)

        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'user-invite-and-profile-academy-with-status-invited-not-found',
            'status_code': 404
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    """
    🔽🔽🔽 GET ProfileAcademy with status INVITED and without UserInvite
    """

    def test_resend_invite__put__profile_academy_with_status_invited(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=1,
                                     capability='read_invite',
                                     role='potato',
                                     syllabus=1)

        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = generate_profile_academy(self, model, model.profile_academy, arguments={})
        # expected = generate_user_invite(self, model, model.user_invite, arguments={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET ProfileAcademy with status INVITED and with UserInvite
    """

    def test_resend_invite__put__profile_academy_with_status_invited__(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=1,
                                     capability='read_invite',
                                     role='potato',
                                     user_invite=1,
                                     syllabus=1)

        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})
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

        model = self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1359})
        response = self.client.put(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: invite_resend for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT ProfileAcademy not found
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_resend_invite__put__profile_academy_not_found(self):
        """Test """
        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=1, role=1, capability='invite_resend')
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 2})
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'profile-academy-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 PUT with ProfileAcademy
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_resend_invite__put__with_profile_academy(self):
        """Test """
        self.headers(academy=1)

        model = self.generate_models(authenticate=True, profile_academy=1, role=1, capability='invite_resend')
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = generate_profile_academy(self, model, model.profile_academy, arguments={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(actions.send_email_message.call_args_list, generate_send_email_message(self, model))

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
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})
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
        url = reverse_lazy('authenticate:academy_member_id_invite', kwargs={'profileacademy_id': 1})
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
