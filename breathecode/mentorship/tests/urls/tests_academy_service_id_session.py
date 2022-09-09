"""
This file just can contains duck tests refert to AcademyInviteView
"""
from datetime import timedelta
import hashlib
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils.datetime_interger import duration_to_str

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import MentorshipTestCase
from django.utils import timezone

UTC_NOW = timezone.now()


def get_tooltip(obj):

    message = f'This mentorship should last no longer than {int(obj.service.duration.seconds/60)} min. <br />'
    if obj.started_at is None:
        message += 'The mentee never joined the session. <br />'
    else:
        message += f'Started on {obj.started_at.strftime("%m/%d/%Y at %H:%M:%S")}. <br />'
        if obj.mentor_joined_at is None:
            message += f'The mentor never joined'
        elif obj.mentor_joined_at > obj.started_at:
            message += f'The mentor joined {duration_to_str(obj.mentor_joined_at - obj.started_at)} before. <br />'
        elif obj.started_at > obj.mentor_joined_at:
            message += f'The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />'

        if obj.ended_at is not None:
            message += f'The mentorship lasted {duration_to_str(obj.ended_at - obj.started_at)}. <br />'
            if (obj.ended_at - obj.started_at) > obj.mentor.service.duration:
                extra_time = (obj.ended_at - obj.started_at) - obj.mentor.service.duration
                message += f'With extra time of {duration_to_str(extra_time)}. <br />'
            else:
                message += f'No extra time detected <br />'
        else:
            message += f'The mentorship has not ended yet. <br />'
            if obj.ends_at is not None:
                message += f'But it was supposed to end after {duration_to_str(obj.ends_at - obj.started_at)} <br />'

    return message


def get_duration_string(obj):

    if obj.started_at is None:
        return 'Never started'

    end_date = obj.ended_at
    if end_date is None:
        return 'Never ended'

    if obj.started_at > end_date:
        return 'Ended before it started'

    if (end_date - obj.started_at).days > 1:
        return f'Many days'

    return duration_to_str(obj.ended_at - obj.started_at)


def get_billed_str(obj):
    return duration_to_str(obj.accounted_duration)


def get_accounted_duration_string(obj):
    return duration_to_str(obj.accounted_duration)


def get_extra_time(obj):

    if obj.started_at is None or obj.ended_at is None:
        return None

    if (obj.ended_at - obj.started_at).days > 1:
        return f'Many days of extra time, probably it was never closed'

    if (obj.ended_at - obj.started_at) > obj.mentor.service.duration:
        extra_time = (obj.ended_at - obj.started_at) - obj.mentor.service.duration
        return f'Extra time of {duration_to_str(extra_time)}, the expected duration was {duration_to_str(obj.mentor.service.duration)}'
    else:
        return None


def get_mentor_late(obj):

    if obj.started_at is None or obj.mentor_joined_at is None:
        return None

    if obj.started_at > obj.mentor_joined_at and (obj.started_at - obj.mentor_joined_at).seconds > (60 * 4):
        return f'The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />'
    else:
        return None


def get_mente_joined(obj):

    if obj.started_at is None:
        return 'Session did not start because mentee never joined'
    else:
        return True


def get_rating(obj):

    answer = obj.answer_set.first()
    if answer is None:
        return None

    # build it if is necessary
    # else:
    #     return AnswerSmallSerializer(answer).data


def get_serializer(self, mentorship_session, mentor_profile, mentorship_service, user, data={}):
    return {
        'accounted_duration':
        mentorship_session.accounted_duration,
        'billed_str':
        get_billed_str(mentorship_session),
        'duration_string':
        get_duration_string(mentorship_session),
        'ended_at':
        self.bc.datetime.to_iso_string(mentorship_session.ended_at) if mentorship_session.ended_at else None,
        'extra_time':
        get_extra_time(mentorship_session),
        'id':
        mentorship_session.id,
        'mentee_joined':
        get_mente_joined(mentorship_session),
        'mentee': {
            'email': user.email,
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'mentee_left_at':
        mentorship_session.mentee_left_at,
        'mentor': {
            'booking_url':
            mentor_profile.booking_url,
            'created_at':
            self.bc.datetime.to_iso_string(mentor_profile.created_at),
            'email':
            mentor_profile.email,
            'id':
            mentor_profile.id,
            'one_line_bio':
            mentor_profile.one_line_bio,
            'online_meeting_url':
            mentor_profile.online_meeting_url,
            'price_per_hour':
            mentor_profile.price_per_hour,
            'rating':
            mentor_profile.rating,
            'services': [{
                'academy': {
                    'icon_url': mentorship_service.academy.icon_url,
                    'id': mentorship_service.academy.id,
                    'logo_url': mentorship_service.academy.logo_url,
                    'name': mentorship_service.academy.name,
                    'slug': mentorship_service.academy.slug,
                },
                'allow_mentee_to_extend':
                mentorship_service.allow_mentee_to_extend,
                'allow_mentors_to_extend':
                mentorship_service.allow_mentors_to_extend,
                'created_at':
                self.bc.datetime.to_iso_string(mentorship_service.created_at),
                'duration':
                self.bc.datetime.from_timedelta(mentorship_service.duration),
                'id':
                mentorship_service.id,
                'language':
                mentorship_service.language,
                'logo_url':
                mentorship_service.logo_url,
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
                'updated_at':
                self.bc.datetime.to_iso_string(mentorship_service.updated_at),
            }],
            'slug':
            mentor_profile.slug,
            'status':
            mentor_profile.status,
            'timezone':
            mentor_profile.timezone,
            'updated_at':
            self.bc.datetime.to_iso_string(mentor_profile.updated_at),
            'user': {
                'email': user.email,
                'first_name': user.first_name,
                'id': user.id,
                'last_name': user.last_name,
            }
        },
        'mentor_joined_at':
        mentorship_session.mentor_joined_at,
        'mentor_late':
        get_mentor_late(mentorship_session),
        'mentor_left_at':
        mentorship_session.mentor_left_at,
        'rating':
        get_rating(mentorship_session),
        'started_at':
        self.bc.datetime.to_iso_string(mentorship_session.started_at)
        if mentorship_session.started_at else None,
        'status':
        mentorship_session.status,
        'status_message':
        mentorship_session.status_message,
        'suggested_accounted_duration':
        mentorship_session.suggested_accounted_duration,
        'summary':
        mentorship_session.summary,
        'tooltip':
        get_tooltip(mentorship_session),
        **data,
    }


def mentor_profile_columns(data={}):
    token = hashlib.sha1(
        (str(data['slug'] if 'slug' in data else '') + str(UTC_NOW)).encode('UTF-8')).hexdigest()
    return {
        'bio': None,
        'booking_url': None,
        'email': None,
        'id': 0,
        'name': '',
        'online_meeting_url': None,
        'price_per_hour': 0,
        'service_id': 0,
        'slug': 'mirai-nikki',
        'status': 'INVITED',
        'timezone': None,
        'token': token,
        'user_id': 0,
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
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

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
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

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_mentorship_session for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
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
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService
    """

    def test__get__with_two_mentor_profile(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=2,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
        response = self.client.get(url)

        json = response.json()
        mentorship_session_list = sorted(model.mentorship_session, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self,
                           mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}) for mentorship_session in mentorship_session_list
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipSession'),
            self.bc.format.to_dict(model.mentorship_session),
        )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing status
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_bad_status(self):
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']

        for n in range(0, 4):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_sessions = [{'status': x} for x in choices]
            bad_statuses = ','.join([x for x in statuses if x not in choices])
            model = self.bc.database.create(user=1,
                                            role=1,
                                            capability='read_mentorship_session',
                                            mentorship_session=mentorship_sessions,
                                            mentor_profile=1,
                                            mentorship_service=1,
                                            profile_academy=1)

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                   f'?status={bad_statuses}'
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of('mentorship.MentorshipSession'),
                self.bc.format.to_dict(model.mentorship_session),
            )

            # teardown
            self.bc.database.delete('mentorship.MentorshipSession')

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_status(self):
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']

        for n in range(0, 4):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_sessions = [{'status': x} for x in choices]
            model = self.bc.database.create(user=1,
                                            role=1,
                                            capability='read_mentorship_session',
                                            mentorship_session=mentorship_sessions,
                                            mentor_profile=1,
                                            mentorship_service=1,
                                            profile_academy=1)

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = (reverse_lazy('mentorship:academy_service_id_session',
                                kwargs={'service_id': model.mentor_profile.id}) +
                   f'?status={first_status},{second_status}')
            response = self.client.get(url)

            json = response.json()
            mentorship_session_list = sorted(model.mentorship_session,
                                             key=lambda x: x.created_at,
                                             reverse=True)
            expected = [
                get_serializer(self,
                               mentorship_session_list[0],
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={'status': second_status}),
                get_serializer(self,
                               mentorship_session_list[1],
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={'status': first_status}),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of('mentorship.MentorshipSession'),
                self.bc.format.to_dict(model.mentorship_session),
            )

            # teardown
            self.bc.database.delete('mentorship.MentorshipSession')

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing billed
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_billed_as_true__without_mentorship_bill(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?billed=true'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_billed_as_true__with_mentorship_bill(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_bill=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?billed=true'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_billed_as_false__with_mentorship_bill(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_bill=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?billed=false'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_billed_as_false__without_mentorship_bill(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?billed=false'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing started_after
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_bad_started_after(self):
        utc_now = timezone.now()
        mentorship_session = {'started_at': utc_now}
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?started_after={self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_started_after(self):
        utc_now = timezone.now()
        mentorship_session = {'started_at': utc_now}
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?started_after={self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_started_after__without_started_at(self):
        utc_now = timezone.now()
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        cases = [
            self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1)),
            self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1)),
        ]
        for case in cases:
            url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                    f'?started_after={case}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                get_serializer(self,
                               model.mentorship_session,
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={}),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
                self.bc.format.to_dict(model.mentorship_session),
            ])

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing ended_before
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_bad_ended_before(self):
        utc_now = timezone.now()
        mentorship_session = {'ended_at': utc_now}
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?ended_before={self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_ended_before(self):
        utc_now = timezone.now()
        mentorship_session = {'ended_at': utc_now}
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                f'?ended_before={self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1))}'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session,
                           model.mentor_profile,
                           model.mentorship_service,
                           model.user,
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__get__with_two_mentor_profile__passing_ended_before__without_ended_at(self):
        utc_now = timezone.now()
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user)

        cases = [
            self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1)),
            self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1)),
        ]

        for case in cases:
            url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + \
                    f'?ended_before={case}'
            response = self.client.get(url)

            json = response.json()
            expected = [
                get_serializer(self,
                               model.mentorship_session,
                               model.mentor_profile,
                               model.mentorship_service,
                               model.user,
                               data={}),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
                self.bc.format.to_dict(model.mentorship_session),
            ])

    """
    🔽🔽🔽 GET with four MentorshipSession, MentorProfile and MentorshipService, passing mentor
    """

    def test__get__with_four_elements__padding_bad_mentor(self):
        mentorship_sessions = [{'mentee_id': x, 'mentor_id': x} for x in range(1, 5)]
        mentor_profiles = [{'user_id': x} for x in range(1, 5)]
        model = self.bc.database.create(user=4,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_sessions,
                                        mentor_profile=mentor_profiles,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + f'?mentor=5,6'
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipSession'),
            self.bc.format.to_dict(model.mentorship_session),
        )

    def test__get__with_four_elements__padding_mentor(self):
        mentorship_sessions = [{'mentee_id': x, 'mentor_id': x} for x in range(1, 5)]
        mentor_profiles = [{'user_id': x} for x in range(1, 5)]
        model = self.bc.database.create(user=4,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=mentorship_sessions,
                                        mentor_profile=mentor_profiles,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1}) + f'?mentor=1,3'
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self,
                           model.mentorship_session[2],
                           model.mentor_profile[2],
                           model.mentorship_service,
                           model.user[2],
                           data={}),
            get_serializer(self,
                           model.mentorship_session[0],
                           model.mentor_profile[0],
                           model.mentorship_service,
                           model.user[0],
                           data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('mentorship.MentorshipSession'),
            self.bc.format.to_dict(model.mentorship_session),
        )

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_service_id_session', kwargs={'service_id': 1})
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension', 'SortExtension']),
        ])

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])
