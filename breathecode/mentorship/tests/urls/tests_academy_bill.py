"""
This file just can contains duck tests refert to AcademyInviteView
"""
from datetime import timedelta
import hashlib
import random
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils.datetime_interger import duration_to_str

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import MentorshipTestCase
from django.utils import timezone

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_serializer(self, mentorship_bill, mentor_profile, mentorship_service, user, data={}):
    return {
        'created_at': format_datetime(self, mentorship_bill.created_at),
        'ended_at': format_datetime(self, mentorship_bill.ended_at),
        'id': mentorship_bill.id,
        'mentor': {
            'booking_url': mentor_profile.booking_url,
            'id': mentor_profile.id,
            'service': {
                'allow_mentee_to_extend':
                mentorship_service.allow_mentee_to_extend,
                'allow_mentors_to_extend':
                mentorship_service.allow_mentors_to_extend,
                'duration':
                self.bc.datetime.from_timedelta(mentorship_service.duration),
                'id':
                mentorship_service.id,
                'language':
                mentorship_service.language,
                'max_duration':
                self.bc.datetime.from_timedelta(mentorship_service.max_duration),
                'missed_meeting_duration':
                self.bc.datetime.from_timedelta(mentorship_service.missed_meeting_duration),
                'name':
                mentorship_service.name,
                'slug':
                mentorship_service.slug,
                'status':
                mentorship_service.status,
            },
            'slug': mentor_profile.slug,
            'status': mentor_profile.status,
            'user': {
                'email': user.email,
                'first_name': user.first_name,
                'id': user.id,
                'last_name': user.last_name,
            },
        },
        'overtime_minutes': float(mentorship_bill.overtime_minutes),
        'paid_at': format_datetime(self, mentorship_bill.ended_at),
        'reviewer': {
            'email': user.email,
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'started_at': format_datetime(self, mentorship_bill.ended_at),
        'status': mentorship_bill.status,
        'total_duration_in_hours': float(mentorship_bill.total_duration_in_hours),
        'total_duration_in_minutes': float(mentorship_bill.total_duration_in_minutes),
        'total_price': float(mentorship_bill.total_price),
        **data,
    }


def post_serializer(data={}):
    return {
        'accounted_duration': None,
        'agenda': None,
        'allow_billing': False,
        'bill': None,
        'ended_at': None,
        'ends_at': None,
        'id': 1,
        'is_online': False,
        'latitude': None,
        'longitude': None,
        'mentee': None,
        'mentee_left_at': None,
        'mentor': 1,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'name': None,
        'online_meeting_url': None,
        'online_recording_url': None,
        'started_at': None,
        'starts_at': None,
        'status': 'PENDING',
        'summary': None,
        **data,
    }


def mentorship_session_columns(data={}):
    return {
        'accounted_duration': None,
        'agenda': None,
        'allow_billing': False,
        'bill_id': None,
        'ended_at': None,
        'ends_at': None,
        'id': 1,
        'is_online': False,
        'latitude': None,
        'longitude': None,
        'mentee_id': None,
        'mentee_left_at': None,
        'mentor_id': 1,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'name': None,
        'online_meeting_url': None,
        'online_recording_url': None,
        'started_at': None,
        'starts_at': None,
        'status': 'PENDING',
        'status_message': None,
        'suggested_accounted_duration': None,
        'summary': None,
        **data,
    }


def get_base_number() -> int:
    return 1 if random.random() < 0.5 else -1


def append_delta_to_datetime(date):
    return date + timedelta(minutes=random.randint(0, 180))


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """
    def test__get__without_auth(self):
        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__get__without_academy_header(self):
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test__get__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_mentorship_bill for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability='read_mentorship_bill', profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        mentorship_bill=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_bill,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService
    """

    def test__get__with_two_mentor_profile(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        mentorship_bill=2,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.get(url)

        json = response.json()
        mentorship_bill_list = sorted(model.mentorship_bill, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self,
                           mentorship_bill,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}) for mentorship_bill in mentorship_bill_list
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipBill'),
            self.bc.format.to_dict(model.mentorship_bill),
        )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing status
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_bad_status(self):
        statuses = ['DUE', 'APPROVED', 'PAID', 'IGNORED']

        for n in range(0, 3):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_bills = [{'status': x} for x in choices]
            bad_statuses = ','.join([x for x in statuses if x not in choices])
            model = self.bc.database.create(user=1,
                                            role=1,
                                            capability='read_mentorship_bill',
                                            mentorship_session=1,
                                            mentorship_bill=mentorship_bills,
                                            mentor_profile=1,
                                            mentorship_service=1,
                                            profile_academy=1)

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('mentorship:academy_bill') + \
                   f'?status={bad_statuses}'
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of('mentorship.MentorshipBill'),
                self.bc.format.to_dict(model.mentorship_bill),
            )

            # teardown
            self.bc.database.delete('mentorship.MentorshipBill')

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_status(self):
        statuses = ['DUE', 'APPROVED', 'PAID', 'IGNORED']

        for n in range(0, 3):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_bills = [{'status': x} for x in choices]
            model = self.bc.database.create(user=1,
                                            role=1,
                                            capability='read_mentorship_bill',
                                            mentorship_session=1,
                                            mentorship_bill=mentorship_bills,
                                            mentor_profile=1,
                                            mentorship_service=1,
                                            profile_academy=1)

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('mentorship:academy_bill') + f'?status={first_status},{second_status}'
            response = self.client.get(url)

            json = response.json()
            mentorship_bill_list = sorted(model.mentorship_bill, key=lambda x: x.created_at, reverse=True)
            expected = [
                get_serializer(self,
                               mentorship_bill_list[0],
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={'status': second_status}),
                get_serializer(self,
                               mentorship_bill_list[1],
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={'status': first_status}),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of('mentorship.MentorshipBill'),
                self.bc.format.to_dict(model.mentorship_bill),
            )

            # teardown
            self.bc.database.delete('mentorship.MentorshipBill')

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing started_after
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__get__with_two_mentor_profile__passing_bad_started_after(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        mentorship_bill=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill') + \
                f'?after={self.bc.datetime.to_iso_string(UTC_NOW + timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__get__with_two_mentor_profile__passing_started_after(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_bill=1,
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill') + \
                f'?after={self.bc.datetime.to_iso_string(UTC_NOW - timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_bill,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing ended_before
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__get__with_two_mentor_profile__passing_bad_ended_before(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        mentorship_bill=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill') + \
                f'?before={self.bc.datetime.to_iso_string(UTC_NOW - timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__get__with_two_mentor_profile__passing_ended_before(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_bill=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill') + \
                f'?before={self.bc.datetime.to_iso_string(UTC_NOW + timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_bill,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

    """
    🔽🔽🔽 GET with four MentorshipSession, MentorProfile and MentorshipService, passing mentor
    """

    def test__get__with_four_elements__padding_bad_mentor(self):
        mentorship_sessions = [{'mentee_id': x, 'mentor_id': x} for x in range(1, 5)]
        mentor_profiles = [{'user_id': x, 'service_id': x} for x in range(1, 5)]
        mentorship_bills = [{'reviewer_id': x, 'mentor_id': x} for x in range(1, 5)]
        model = self.bc.database.create(user=4,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=mentorship_sessions,
                                        mentor_profile=mentor_profiles,
                                        mentorship_bill=mentorship_bills,
                                        mentorship_service=4,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('mentorship:academy_bill') + f'?mentor=5,6'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipBill'),
            self.bc.format.to_dict(model.mentorship_bill),
        )

    def test__get__with_four_elements__padding_mentor(self):
        mentorship_sessions = [{'mentee_id': x, 'mentor_id': x} for x in range(1, 5)]
        mentor_profiles = [{'user_id': x, 'service_id': x} for x in range(1, 5)]
        mentorship_bills = [{'reviewer_id': x, 'mentor_id': x} for x in range(1, 5)]
        model = self.bc.database.create(user=4,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=mentorship_sessions,
                                        mentorship_bill=mentorship_bills,
                                        mentor_profile=mentor_profiles,
                                        mentorship_service=4,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('mentorship:academy_bill') + f'?mentor=1,3'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_bill[2],
                           model.mentor_profile[2],
                           model.mentorship_service[2],
                           model.user[2],
                           data={}),
            get_serializer(self,
                           model.mentorship_bill[0],
                           model.mentor_profile[0],
                           model.mentorship_service[0],
                           model.user[0],
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipBill'),
            self.bc.format.to_dict(model.mentorship_bill),
        )

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_bill',
                                        mentorship_session=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension', 'SortExtension']),
        ])

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])

    """
    🔽🔽🔽 POST capability
    """

    def test__post__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.post(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_mentorship_bill for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 POST with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__post__missing_fields(self):
        model = self.bc.database.create(user=1, role=1, capability='crud_mentorship_bill', profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_bill')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'argument-not-provided', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])
