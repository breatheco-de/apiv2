"""
Test /v1/auth/subscribe
"""
import hashlib
from datetime import datetime
import os
import random
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
import pytest
from rest_framework import status

from breathecode.notify import actions as notify_actions
from breathecode.authenticate.models import Token

from ..mixins.new_auth_test_case import AuthTestCase

now = timezone.now()


def user_db_item(data={}):
    return {
        'email': '',
        'first_name': '',
        'id': 0,
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'last_login': None,
        'last_name': '',
        'password': '',
        'username': '',
        **data,
    }


def plan_db_item(plan, data={}):
    return {
        'id': plan.id,
        'event_type_set_id': plan.event_type_set.id if plan.event_type_set else None,
        'mentorship_service_set_id': plan.mentorship_service_set.id if plan.mentorship_service_set else None,
        'cohort_set_id': plan.cohort_set.id if plan.cohort_set else None,
        'currency_id': plan.currency.id,
        'slug': plan.slug,
        'status': plan.status,
        'has_waiting_list': plan.has_waiting_list,
        'is_onboarding': plan.is_onboarding,
        'time_of_life': plan.time_of_life,
        'time_of_life_unit': plan.time_of_life_unit,
        'trial_duration': plan.trial_duration,
        'trial_duration_unit': plan.trial_duration_unit,
        'is_renewable': plan.is_renewable,
        'owner_id': plan.owner.id if plan.owner else None,
        'price_per_half': plan.price_per_half,
        'price_per_month': plan.price_per_month,
        'price_per_quarter': plan.price_per_quarter,
        'price_per_year': plan.price_per_year,
        **data,
    }


def user_invite_db_item(data={}):
    return {
        'academy_id': None,
        'author_id': None,
        'cohort_id': None,
        'id': 1,
        'role_id': None,
        'sent_at': None,
        'status': 'PENDING',
        'is_email_validated': False,
        'token': '',
        'process_message': '',
        'process_status': 'PENDING',
        'syllabus_id': None,
        'user_id': None,
        **data,
    }


def plan_serializer(plan):
    return {
        'financing_options': [],
        'service_items': [],
        'has_available_cohorts': bool(plan.cohort_set),
        'slug': plan.slug,
        'status': plan.status,
        'time_of_life': plan.time_of_life,
        'time_of_life_unit': plan.time_of_life_unit,
        'trial_duration': plan.trial_duration,
        'trial_duration_unit': plan.trial_duration_unit,
    }


def post_serializer(plans=[], data={}):
    return {
        'id': 0,
        'access_token': None,
        'cohort': None,
        'syllabus': None,
        'email': '',
        'first_name': '',
        'last_name': '',
        'phone': '',
        'plans': [plan_serializer(plan) for plan in plans],
        **data,
    }


def put_serializer(user_invite, cohort=None, syllabus=None, plans=[], data={}):
    return {
        'id': user_invite.id,
        'access_token': None,
        'cohort': cohort.id if cohort else None,
        'syllabus': syllabus.id if syllabus else None,
        'email': user_invite.email,
        'first_name': user_invite.first_name,
        'last_name': user_invite.last_name,
        'phone': user_invite.phone,
        'plans': [plan_serializer(plan) for plan in plans],
        **data,
    }


b = os.urandom(64)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr('os.urandom', lambda _: b)
    yield


class SubscribeTestSuite(AuthTestCase):
    """Test /v1/auth/subscribe"""
    """
    🔽🔽🔽 Post without email
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__without_email(self):
        url = reverse_lazy('authenticate:subscribe')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'without-email', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    """
    🔽🔽🔽 Post without UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__without_user_invite(self):
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123'
        }

        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        json = response.json()
        expected = post_serializer(data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             'user_id': 1,
                             'academy_id': None,
                             'author_id': None,
                             'cohort_id': None,
                             'id': 1,
                             'is_email_validated': False,
                             'role_id': None,
                             'sent_at': None,
                             'status': 'ACCEPTED',
                             'token': hashlib.sha512('pokemon@potato.io'.encode('UTF-8') + b).hexdigest(),
                             'process_message': '',
                             'process_status': 'DONE',
                             'syllabus_id': None,
                             **data,
                         }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    """
    🔽🔽🔽 Post with UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists__status_waiting_list(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'pokemon@potato.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'user-invite-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists__status_pending__academy_no_saas(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'pokemon@potato.io', 'status': 'PENDING'}
        academy = {'available_as_saas': False}
        model = self.bc.database.create(user_invite=user_invite, academy=academy)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'invite-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists__status_pending__academy_no_saas__from_cohort(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'pokemon@potato.io', 'status': 'PENDING', 'academy_id': None}
        academy = {'available_as_saas': False}
        model = self.bc.database.create(user_invite=user_invite, academy=academy, cohort=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'invite-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists__status_pending(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invites = [{'email': 'pokemon@potato.io', 'status': x} for x in ['PENDING', 'ACCEPTED']]
        model = self.bc.database.create(user_invite=user_invites)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {'detail': 'user-invite-exists-status-pending', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            self.bc.format.to_dict(model.user_invite),
        )

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__already_exists__status_accepted(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'pokemon@potato.io', 'status': 'ACCEPTED'}
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {
            'detail': 'user-invite-exists-status-accepted',
            'status_code': 400,
            'silent': True,
            'silent_code': 'user-invite-exists-status-accepted',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    """
    🔽🔽🔽 Post with UserInvite
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    def test_task__post__with_user_invite__user_exists(self):
        """
        Descriptions of models are being generated:

          User(id=1):
            groups: []
            user_permissions: []
        """

        user = {'email': 'pokemon@potato.io'}
        model = self.bc.database.create(user=user)

        url = reverse_lazy('authenticate:subscribe')
        data = {'email': 'pokemon@potato.io'}
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {
            'detail': 'user-exists',
            'silent': True,
            'silent_code': 'user-exists',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

    """
    🔽🔽🔽 Post with UserInvite with other email
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__post__with_user_invite(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'henrrieta@horseman.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123'
        }

        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        json = response.json()
        expected = post_serializer(data={
            'id': 2,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite), {
                'user_id': 1,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 2,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'syllabus_id': None,
                **data,
            }
        ])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call(
                'verify_email', 'pokemon@potato.io', {
                    'SUBJECT':
                    '4Geeks - Validate account',
                    'LINK': ('http://localhost:8000/v1/auth/password/' +
                             hashlib.sha512('pokemon@potato.io'.encode('UTF-8') + b).hexdigest())
                })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Post does not get in waiting list using a plan
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__post__does_not_get_in_waiting_list_using_a_plan(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'henrrieta@horseman.io', 'status': 'WAITING_LIST'}
        plan = {'time_of_life': None, 'time_of_life_unit': None, 'has_waiting_list': True, 'invites': []}
        model = self.bc.database.create(user_invite=user_invite, plan=plan)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'plan': 1,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['plan']
        json = response.json()
        expected = put_serializer(model.user_invite, plans=[model.plan], data={
            'id': 2,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite), {
                'user_id': None,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 2,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'WAITING_LIST',
                'process_message': '',
                'process_status': 'PENDING',
                'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                'syllabus_id': None,
                **data,
            }
        ])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [plan_db_item(model.plan, data={})])
        self.bc.check.queryset_with_pks(model.plan.invites.all(), [2])
        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Post get in waiting list using a plan
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__post__get_in_waiting_list_using_a_plan(self):
        """
        Descriptions of models are being generated:

          UserInvite(id=1): {}
        """

        user_invite = {'email': 'henrrieta@horseman.io', 'status': 'WAITING_LIST'}
        plan = {'time_of_life': None, 'time_of_life_unit': None, 'has_waiting_list': False, 'invites': []}
        model = self.bc.database.create(user_invite=user_invite, plan=plan)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'plan': 1,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['plan']
        json = response.json()
        expected = post_serializer(plans=[model.plan], data={
            'id': 2,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite), {
                'user_id': 1,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 2,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'syllabus_id': None,
                **data,
            }
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [plan_db_item(model.plan, data={})])
        self.bc.check.queryset_with_pks(model.plan.invites.all(), [2])

        token = hashlib.sha512('pokemon@potato.io'.encode('UTF-8') + b).hexdigest()

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        User = self.bc.database.get_model('auth.User')
        user = User.objects.get(email=data['email'])

        self.bc.check.calls(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # When: Syllabus is passed and does not exist
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__syllabus_does_not_exists(self):
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': random.choice([self.bc.fake.slug(), random.randint(1, 100)]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['syllabus']
        json = response.json()
        expected = {'detail': 'syllabus-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # When: Course is passed and does not exist
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__course_does_not_exists(self):
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([self.bc.fake.slug(), random.randint(1, 100)]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']
        json = response.json()
        expected = {'detail': 'course-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Course
    # When: Course is passed as slug and exists
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__course_without_syllabus(self):
        model = self.bc.database.create(course=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']
        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(
                data={
                    'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                    'process_status': 'DONE',
                    'status': 'ACCEPTED',
                    'academy_id': 1,
                    'user_id': 1,
                    **data,
                }),
        ])

        del data['phone']
        users = [x for x in self.bc.database.list_of('auth.User') if x.pop('date_joined')]

        self.assertEqual(users, [
            user_db_item(data={
                **data,
                'id': 1,
                'username': 'pokemon@potato.io',
            }),
        ])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        token = hashlib.sha512('pokemon@potato.io'.encode('UTF-8') + b).hexdigest()

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        User = self.bc.database.get_model('auth.User')
        user = User.objects.get(email=data['email'])

        self.bc.check.calls(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Given: 1 Course
    # When: Course is passed as slug and exists
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__course_and_syllabus(self):
        model = self.bc.database.create(course=1, syllabus=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']
        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(
                data={
                    'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                    'process_status': 'DONE',
                    'status': 'ACCEPTED',
                    'academy_id': 1,
                    'user_id': 1,
                    **data,
                }),
        ])

        del data['phone']
        del data['syllabus_id']
        users = [x for x in self.bc.database.list_of('auth.User') if x.pop('date_joined')]

        self.assertEqual(users, [
            user_db_item(data={
                **data,
                'id': 1,
                'username': 'pokemon@potato.io',
            }),
        ])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        token = hashlib.sha512('pokemon@potato.io'.encode('UTF-8') + b).hexdigest()

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        User = self.bc.database.get_model('auth.User')
        user = User.objects.get(email=data['email'])

        self.bc.check.calls(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Given: 1 Course and 1 Syllabus
    # When: Course is passed as slug and exists, course is not associated to syllabus
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__course_and_syllabus__syllabus_not_associated_to_course(self):
        course = {'syllabus': []}
        syllabus = {'slug': self.bc.fake.slug()}
        model = self.bc.database.create(course=course, syllabus=syllabus)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
            # 'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']

        json = response.json()
        expected = {'detail': 'syllabus-not-belong-to-course', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        del data['syllabus']

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Course, 1 Syllabus
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__course_and_syllabus__waiting_list(self):
        course = {'has_waiting_list': True, 'invites': []}
        model = self.bc.database.create(course=course, syllabus=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']

        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': None,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(
                data={
                    'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                    'process_status': 'PENDING',
                    'status': 'WAITING_LIST',
                    'academy_id': 1,
                    **data,
                }),
        ])

        del data['phone']
        del data['syllabus_id']

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Course, 1 UserInvite and 1 Syllabus
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__with_other_invite__course_and_syllabus__waiting_list(self):
        course = {'has_waiting_list': True, 'invites': []}
        user_invite = {'email': 'pokemon@potato.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(course=course, syllabus=1, user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['course']

        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 2,
            'access_token': None,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
            user_invite_db_item(
                data={
                    'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                    'process_status': 'PENDING',
                    'status': 'WAITING_LIST',
                    'academy_id': 1,
                    **data,
                    'id': 2,
                }),
        ])

        del data['phone']
        del data['syllabus_id']

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [2])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Plan and 1 UserInvite
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__with_other_invite__plan__waiting_list(self):
        plan = {'has_waiting_list': True, 'invites': [], 'time_of_life': None, 'time_of_life_unit': None}
        user_invite = {'email': 'pokemon@potato.io', 'status': 'WAITING_LIST'}
        model = self.bc.database.create(plan=plan, user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'plan': random.choice([model.plan.id, model.plan.slug]),
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['plan']

        json = response.json()
        expected = post_serializer(plans=[model.plan], data={
            'id': 2,
            'access_token': None,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
            user_invite_db_item(
                data={
                    'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                    'process_status': 'PENDING',
                    'status': 'WAITING_LIST',
                    'academy_id': None,
                    **data,
                    'id': 2,
                }),
        ])

        del data['phone']

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [
            self.bc.format.to_dict(model.plan),
        ])

        self.bc.check.queryset_with_pks(model.plan.invites.all(), [2])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Cohort and 1 UserInvite
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__with_other_invite__cohort__waiting_list(self):
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'cohort_id': None,
            'syllabus_id': None
        }
        model = self.bc.database.create(cohort=1, user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'cohort': model.cohort.id,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['cohort']

        json = response.json()
        expected = post_serializer(plans=[],
                                   data={
                                       'id': 2,
                                       'access_token': access_token,
                                       'cohort': 1,
                                       **data,
                                   })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        token = hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest()
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
            user_invite_db_item(
                data={
                    'token': token,
                    'status': 'ACCEPTED',
                    'process_message': '',
                    'process_status': 'DONE',
                    'academy_id': 1,
                    'cohort_id': 1,
                    'user_id': 1,
                    **data,
                    'id': 2,
                }),
        ])

        del data['phone']

        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Given: 1 Syllabus and 1 UserInvite
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__post__with_other_invite__syllabus__waiting_list(self):
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'cohort_id': None,
            'syllabus_id': None
        }
        model = self.bc.database.create(syllabus=1, user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': model.syllabus.id,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.post(url, data, format='json')

        del data['syllabus']

        json = response.json()
        expected = post_serializer(plans=[],
                                   data={
                                       'id': 2,
                                       'access_token': access_token,
                                       'syllabus': 1,
                                       **data,
                                   })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        token = hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest()
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
            user_invite_db_item(
                data={
                    'token': token,
                    'status': 'ACCEPTED',
                    'process_message': '',
                    'process_status': 'DONE',
                    'academy_id': None,
                    'syllabus_id': 1,
                    'user_id': 1,
                    **data,
                    'id': 2,
                }),
        ])

        del data['phone']

        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Put a case syllabus not found and syllabus with course
    """
    🔽🔽🔽 Put without email
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__without_email(self):
        url = reverse_lazy('authenticate:subscribe')
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort as None
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__cohort_as_none(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'token': token,
        }

        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()

        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': None,
                **data,
            }])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__cohort_not_found(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'cohort': 1,
            'token': token,
        }
        response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = {'cohort': ['Invalid pk "1" - object does not exist.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': None,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'id': 1,
                'role_id': None,
                'sent_at': None,
                'is_email_validated': False,
                'status': 'WAITING_LIST',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'PENDING',
                'token': token,
                'email': 'pokemon@potato.io',
                'first_name': None,
                'last_name': None,
                'phone': '',
                'syllabus_id': None,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])
        self.assertEqual(self.bc.database.list_of('auth.User'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__cohort_found(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        model = self.bc.database.create(user_invite=user_invite, cohort=1)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'cohort': 1,
            'token': token,
        }

        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['cohort']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': 1,
                'author_id': None,
                'cohort_id': 1,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': None,
                **data,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__cohort_found__academy_available_as_saas__user_does_not_exists(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        academy = {'available_as_saas': True}
        model = self.bc.database.create(user_invite=user_invite, cohort=1, academy=academy)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'cohort': 1,
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['cohort']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': 1,
                'author_id': None,
                'cohort_id': 1,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': None,
                **data,
            }])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User exists
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__cohort_found__academy_available_as_saas__user_exists(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        academy = {'available_as_saas': True}
        user = {'email': 'pokemon@potato.io'}
        model = self.bc.database.create(user_invite=user_invite, cohort=1, academy=academy, user=user)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'cohort': 1,
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['cohort']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': 1,
                'author_id': 1,
                'cohort_id': 1,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': None,
                **data,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])
        self.assertEqual(self.bc.database.list_of('auth.User'), [self.bc.format.to_dict(model.user)])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=model.user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Syllabus not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__syllabus_not_found(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': 1,
            'token': token,
        }
        response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = {'detail': 'syllabus-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': None,
                'academy_id': None,
                'author_id': None,
                'cohort_id': None,
                'is_email_validated': False,
                'id': 1,
                'role_id': None,
                'sent_at': None,
                'status': 'WAITING_LIST',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'PENDING',
                'token': token,
                'email': 'pokemon@potato.io',
                'first_name': None,
                'last_name': None,
                'phone': '',
                'syllabus_id': None,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])
        self.assertEqual(self.bc.database.list_of('auth.User'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Put with UserInvite, passing Syllabus and it found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__syllabus_found(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        model = self.bc.database.create(user_invite=user_invite, cohort=1, syllabus_version=1)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': 1,
            'token': token,
        }

        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()

        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['syllabus']
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            {
                'user_id': 1,
                'academy_id': 1,
                'author_id': None,
                'cohort_id': None,
                'id': 1,
                'role_id': None,
                'is_email_validated': False,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512(('pokemon@potato.io').encode('UTF-8') + b).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': 1,
                **data,
            },
        ])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Syllabus and it found, Academy available as saas, User does not exists
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__syllabus_found__academy_available_as_saas__user_does_not_exists(
            self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        academy = {'available_as_saas': True}
        model = self.bc.database.create(user_invite=user_invite,
                                        cohort=1,
                                        syllabus_version=1,
                                        academy=academy)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': 1,
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['syllabus']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': 1,
                'author_id': None,
                'cohort_id': None,
                'id': 1,
                'role_id': None,
                'is_email_validated': False,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': 1,
                **data,
            }])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Syllabus and it found, Academy available as saas, User exists
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__with_user_invite__syllabus_found__academy_available_as_saas__user_exists(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        academy = {'available_as_saas': True}
        user = {'email': 'pokemon@potato.io'}
        model = self.bc.database.create(user_invite=user_invite,
                                        cohort=1,
                                        syllabus_version=1,
                                        syllabus=1,
                                        academy=academy,
                                        user=user)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'syllabus': 1,
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = put_serializer(model.user_invite, data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        del data['syllabus']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': 1,
                'academy_id': 1,
                'author_id': 1,
                'cohort_id': None,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'ACCEPTED',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'DONE',
                'token': token,
                'syllabus_id': 1,
                **data,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])
        self.assertEqual(self.bc.database.list_of('auth.User'), [self.bc.format.to_dict(model.user)])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=model.user, token_type='login'),
        ])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
    Plan does not exists
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__plan_does_not_exist(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        academy = {'available_as_saas': True}
        self.bc.database.create(user_invite=user_invite, cohort=1, academy=academy)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            # 'cohort': 1,
            'token': token,
            'plan': 1,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']

        json = response.json()
        expected = {'detail': 'plan-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # del data['cohort']
        self.assertEqual(
            self.bc.database.list_of('authenticate.UserInvite'),
            [{
                'user_id': None,
                'academy_id': 1,
                'author_id': None,
                'cohort_id': 1,
                'id': 1,
                'is_email_validated': False,
                'role_id': None,
                'sent_at': None,
                'status': 'WAITING_LIST',
                'email': 'pokemon@potato.io',
                'first_name': None,
                'last_name': None,
                'phone': '',
                'token': hashlib.sha512((str(now) + 'pokemon@potato.io').encode('UTF-8')).hexdigest(),
                'process_message': '',
                'process_status': 'PENDING',
                'token': token,
                'syllabus_id': None,
            }])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])
        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(user_db, [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
    Plan with has_waiting_list = True
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__plan_has_waiting_list(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
        }
        academy = {'available_as_saas': True}
        plan = {'time_of_life': None, 'time_of_life_unit': None, 'has_waiting_list': True, 'invites': []}
        model = self.bc.database.create(user_invite=user_invite, academy=academy, plan=plan)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'token': token,
            'plan': 1,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['plan']

        json = response.json()
        expected = put_serializer(model.user_invite, plans=[model.plan], data={
            'id': 1,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [{
            'user_id': None,
            'academy_id': 1,
            'author_id': None,
            'cohort_id': None,
            'id': 1,
            'is_email_validated': False,
            'role_id': None,
            'sent_at': None,
            'status': 'WAITING_LIST',
            'process_message': '',
            'process_status': 'PENDING',
            'token': token,
            'syllabus_id': None,
            **data,
        }])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [plan_db_item(model.plan, data={})])
        self.bc.check.queryset_with_pks(model.plan.invites.all(), [1])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.assertEqual(Token.get_or_create.call_args_list, [])

    """
    🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
    Plan with has_waiting_list = False
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test_task__put__plan_has_not_waiting_list(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        academy = {'available_as_saas': True}
        plan = {'time_of_life': None, 'time_of_life_unit': None, 'has_waiting_list': False, 'invites': []}
        model = self.bc.database.create(user_invite=user_invite, cohort=1, academy=academy, plan=plan)
        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'token': token,
            'plan': 1,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['plan']

        json = response.json()
        expected = put_serializer(model.user_invite,
                                  plans=[model.plan],
                                  data={
                                      'id': 1,
                                      'access_token': access_token,
                                      **data,
                                  })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [{
            'user_id': 1,
            'academy_id': 1,
            'author_id': None,
            'cohort_id': None,
            'id': 1,
            'is_email_validated': False,
            'role_id': None,
            'sent_at': None,
            'status': 'ACCEPTED',
            'process_message': '',
            'process_status': 'DONE',
            'token': token,
            'syllabus_id': None,
            **data,
        }])

        user_db = self.bc.database.list_of('auth.User')
        for item in user_db:
            self.assertTrue(isinstance(item['date_joined'], datetime))
            del item['date_joined']

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [plan_db_item(model.plan, data={})])
        self.bc.check.queryset_with_pks(model.plan.invites.all(), [1])

        self.assertEqual(user_db, [{
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'valdomero',
            'password': '',
            'username': 'pokemon@potato.io',
        }])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        user = self.bc.database.get('auth.User', 1, dict=False)
        self.assertEqual(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # When: Course is passed and does not exist
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__put__course_does_not_exists(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        model = self.bc.database.create(user_invite=user_invite)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([self.bc.fake.slug(), random.randint(1, 100)]),
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['course']
        json = response.json()
        expected = {'detail': 'course-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Course
    # When: Course is passed as slug and exists
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__put__course_without_syllabus(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        model = self.bc.database.create(user_invite=user_invite, course=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['course']

        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(
                data={
                    'token': token,
                    'process_status': 'DONE',
                    'status': 'ACCEPTED',
                    'academy_id': 1,
                    'user_id': 1,
                    **data,
                }),
        ])

        del data['phone']
        users = [x for x in self.bc.database.list_of('auth.User') if x.pop('date_joined')]

        self.assertEqual(users, [
            user_db_item(data={
                **data,
                'id': 1,
                'username': 'pokemon@potato.io',
            }),
        ])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        User = self.bc.database.get_model('auth.User')
        user = User.objects.get(email=data['email'])

        self.bc.check.calls(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Given: 1 Course
    # When: Course is passed as slug and exists
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__put__course_and_syllabus(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        model = self.bc.database.create(user_invite=user_invite, course=1, syllabus=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['course']

        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': access_token,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(
                data={
                    'token': token,
                    'process_status': 'DONE',
                    'status': 'ACCEPTED',
                    'academy_id': 1,
                    'user_id': 1,
                    **data,
                }),
        ])

        del data['phone']
        del data['syllabus_id']
        users = [x for x in self.bc.database.list_of('auth.User') if x.pop('date_joined')]

        self.assertEqual(users, [
            user_db_item(data={
                **data,
                'id': 1,
                'username': 'pokemon@potato.io',
            }),
        ])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [
            call('verify_email', 'pokemon@potato.io', {
                'SUBJECT': '4Geeks - Validate account',
                'LINK': f'http://localhost:8000/v1/auth/password/{token}'
            })
        ])

        User = self.bc.database.get_model('auth.User')
        user = User.objects.get(email=data['email'])

        self.bc.check.calls(Token.get_or_create.call_args_list, [
            call(user=user, token_type='login'),
        ])

    # Given: 1 Course and 1 Syllabus
    # When: Course is passed as slug and exists, course is not associated to syllabus
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__put__course_and_syllabus__syllabus_not_associated_to_course(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        course = {'syllabus': []}
        syllabus = {'slug': self.bc.fake.slug()}
        model = self.bc.database.create(user_invite=user_invite, course=course, syllabus=syllabus)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['course']

        json = response.json()
        expected = {'detail': 'syllabus-not-belong-to-course', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        del data['syllabus']

        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])

    # Given: 1 Course, 1 UserInvite and 1 Syllabus
    # When: Course is passed as slug and exists, course with waiting list
    # Then: It should return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.notify.actions.send_email_message', MagicMock(return_value=None))
    @patch('breathecode.authenticate.models.Token.get_or_create', MagicMock(wraps=Token.get_or_create))
    def test__put__course_and_syllabus__waiting_list(self):
        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        user_invite = {
            'email': 'pokemon@potato.io',
            'status': 'WAITING_LIST',
            'token': token,
            'cohort_id': None,
        }
        course = {'has_waiting_list': True, 'invites': []}
        model = self.bc.database.create(user_invite=user_invite, course=course, syllabus=1)

        url = reverse_lazy('authenticate:subscribe')
        data = {
            'email': 'pokemon@potato.io',
            'first_name': 'lord',
            'last_name': 'valdomero',
            'phone': '+123123123',
            'course': random.choice([model.course.id, model.course.slug]),
            'syllabus': random.choice([model.syllabus.id, model.syllabus.slug]),
            'token': token,
        }
        access_token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('binascii.hexlify', MagicMock(return_value=bytes(access_token, 'utf-8'))):
            response = self.client.put(url, data, format='json')

        del data['token']
        del data['course']

        json = response.json()
        expected = post_serializer(plans=[], data={
            'id': 1,
            'access_token': None,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data['syllabus_id'] = data.pop('syllabus')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            user_invite_db_item(data={
                'token': token,
                'process_status': 'PENDING',
                'status': 'WAITING_LIST',
                'academy_id': 1,
                **data,
            }),
        ])

        del data['phone']
        del data['syllabus_id']

        self.assertEqual(self.bc.database.list_of('auth.User'), [])
        self.assertEqual(self.bc.database.list_of('marketing.Course'), [
            self.bc.format.to_dict(model.course),
        ])

        self.bc.check.queryset_with_pks(model.course.invites.all(), [1])
        self.assertEqual(self.bc.database.list_of('payments.Plan'), [])

        self.bc.check.calls(notify_actions.send_email_message.call_args_list, [])
        self.bc.check.calls(Token.get_or_create.call_args_list, [])
