"""
Test cases for /academy/:id/member/:id
"""
from datetime import timedelta
import random
import timeago
from unittest.mock import MagicMock, patch
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from django.utils import timezone
from breathecode.mentorship.exceptions import ExtendSessionException
from breathecode.mentorship.models import MentorshipSession

from breathecode.tests.mocks.requests import apply_requests_request_mock
from ..mixins import MentorshipTestCase
from django.core.handlers.wsgi import WSGIRequest

UTC_NOW = timezone.now()
URL = 'https://netscape.bankruptcy.story'
ROOM_NAME = 'carlos-two'
ROOM_URL = ''
API_KEY = random.randint(1, 1000000000)

#FIXME: ends this tests


def apply_get_env(configuration={}):
    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


def get_empty_mentorship_session_queryset(*args, **kwargs):
    return MentorshipSession.objects.filter(id=0)


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def render(message,
           mentor_profile=None,
           token=None,
           mentorship_session=None,
           mentorship_service=None,
           fix_logo=False,
           start_session=False,
           session_expired=False):
    mentor_profile_slug = mentor_profile.slug if mentor_profile else 'asd'
    mentorship_service_slug = mentorship_service.slug if mentorship_service else 'asd'
    environ = {
        'HTTP_COOKIE': '',
        'PATH_INFO': f'/mentor/{mentor_profile_slug}/service/{mentorship_service_slug}',
        'REMOTE_ADDR': '127.0.0.1',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': None,
        'wsgi.errors': None,
        'wsgi.multiprocess': True,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'QUERY_STRING': f'token={token and token.key or ""}',
        'CONTENT_TYPE': 'application/octet-stream'
    }
    request = WSGIRequest(environ)

    context = {
        'MESSAGE': message,
        'BUTTON': None,
        'BUTTON_TARGET': '_blank',
        'LINK': None,
    }

    if start_session:
        context = {
            **context,
            'SUBJECT': 'Mentoring Session',
            'BUTTON': 'Start Session',
            'BUTTON_TARGET': '_self',
            'LINK': f'?token={token.key}&redirect=true',
        }

    if session_expired:
        context = {
            **context,
            'BUTTON': 'End Session',
            'BUTTON_TARGET': '_self',
            'LINK': f'/mentor/session/{mentorship_session.id}?token={token.key}&extend=true',
        }

    string = loader.render_to_string(
        'message.html',
        context,
        request,
        using=None,
    )

    if fix_logo:
        string = string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    if session_expired:
        string = string.replace('&amp;extend=true', '')

    return string


def mentor_serializer(mentor_profile, user, academy):
    return {
        'id': mentor_profile.id,
        'slug': mentor_profile.slug,
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        },
        'service': {
            'id': 1,
            'slug': 'everybody-small',
            'name': 'Savannah Holden DDS',
            'status': 'DRAFT',
            'academy': {
                'id': academy.id,
                'slug': academy.slug,
                'name': academy.name,
                'logo_url': academy.logo_url,
                'icon_url': academy.icon_url,
            },
            'logo_url': None,
            'duration': timedelta(seconds=3600),
            'language': 'en',
            'allow_mentee_to_extend': True,
            'allow_mentors_to_extend': True,
            'max_duration': timedelta(seconds=7200),
            'missed_meeting_duration': timedelta(seconds=600),
            'created_at':...,
            'updated_at':...,
            'description': None
        },
        'status': mentor_profile.status,
        'price_per_hour': mentor_profile.price_per_hour,
        'booking_url': mentor_profile.booking_url,
        'online_meeting_url': mentor_profile.online_meeting_url,
        'timezone': mentor_profile.timezone,
        'syllabus': mentor_profile.syllabus,
        'email': mentor_profile.email,
        'created_at': mentor_profile.created_at,
        'updated_at': mentor_profile.updated_at,
    }


def session_serializer(mentor_profile, user, academy, mentorship_service):
    return [{
        'id': academy.id,
        'status': 'PENDING',
        'started_at': None,
        'ended_at': None,
        'starts_at': None,
        'ends_at':...,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'mentee_left_at': None,
        'allow_billing': True,
        'accounted_duration': None,
        'suggested_accounted_duration': None,
        'mentor': {
            'id': mentor_profile.id,
            'slug': mentor_profile.id,
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
            },
            'service': {
                'id': mentorship_service.id,
                'slug': mentorship_service.slug,
                'name': mentorship_service.name,
                'status': mentorship_service.status,
                'academy': {
                    'id': academy.id,
                    'slug': academy.slug,
                    'name': academy.name,
                    'logo_url': academy.logo_url,
                    'icon_url': academy.icon_url,
                },
                'logo_url': mentorship_service.logo_url,
                'duration': mentorship_service.duration,
                'language': mentorship_service.language,
                'allow_mentee_to_extend': mentorship_service.allow_mentee_to_extend,
                'allow_mentors_to_extend': mentorship_service.allow_mentors_to_extend,
                'max_duration': mentorship_service.max_duration,
                'missed_meeting_duration': mentorship_service.missed_meeting_duration,
                'created_at': mentorship_service.created_at,
                'updated_at': mentorship_service.updated_at,
                'description': mentorship_service.description,
            },
            'status': mentor_profile.status,
            'price_per_hour': mentor_profile.price_per_hour,
            'booking_url': mentor_profile.booking_url,
            'online_meeting_url': mentor_profile.online_meeting_url,
            'timezone': mentor_profile.timezone,
            'syllabus': mentor_profile.syllabus,
            'email': mentor_profile.email,
            'created_at': mentor_profile.created_at,
            'updated_at': mentor_profile.updated_at,
        },
        'mentee': None
    }]


def render_pick_session(mentor_profile, user, token, academy, mentorship_service, fix_logo=False):
    request = None
    base_url = f'/mentor/meet/{mentor_profile.slug}/service/{mentorship_service.slug}?token={token.key}'
    booking_url = mentor_profile.booking_url
    if not booking_url.endswith('?'):
        booking_url += '?'

    context = {
        'token': token.key,
        'mentor': mentor_serializer(mentor_profile, user, academy),
        'SUBJECT': 'Mentoring Session',
        'sessions': session_serializer(mentor_profile, user, academy, mentorship_service),
        'baseUrl': base_url,
    }

    string = loader.render_to_string('pick_session.html', context, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def render_pick_mentee(mentor_profile, user, token, academy, mentorship_service, fix_logo=False):
    request = None
    base_url = f'/mentor/meet/{mentor_profile.slug}/service/{mentorship_service.slug}?token={token.key}&session={academy.id}'
    booking_url = mentor_profile.booking_url
    if not booking_url.endswith('?'):
        booking_url += '?'

    context = {
        'token': token.key,
        'mentor': mentor_serializer(mentor_profile, user, academy),
        'SUBJECT': 'Mentoring Session',
        'sessions': session_serializer(mentor_profile, user, academy, mentorship_service),
        'baseUrl': base_url,
    }

    string = loader.render_to_string('pick_mentee.html', context, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def get_mentorship_session_serializer(mentorship_session, mentor_profile, user, mentorship_service, academy):
    return {
        'id': mentorship_session.id,
        'status': mentorship_session.status,
        'started_at': mentorship_session.started_at,
        'ended_at': mentorship_session.ended_at,
        'starts_at': mentorship_session.starts_at,
        'ends_at': mentorship_session.ends_at,
        'mentor_joined_at': mentorship_session.mentor_joined_at,
        'mentor_left_at': mentorship_session.mentor_left_at,
        'mentee_left_at': mentorship_session.mentee_left_at,
        'allow_billing': mentorship_session.allow_billing,
        'accounted_duration': mentorship_session.accounted_duration,
        'suggested_accounted_duration': mentorship_session.suggested_accounted_duration,
        'mentor': {
            'id': mentor_profile.id,
            'slug': mentor_profile.slug,
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
            },
            'service': {
                'id': mentorship_service.id,
                'slug': mentorship_service.slug,
                'name': mentorship_service.name,
                'status': mentorship_service.status,
                'academy': {
                    'id': academy.id,
                    'slug': academy.slug,
                    'name': academy.name,
                    'logo_url': academy.logo_url,
                    'icon_url': academy.icon_url,
                },
                'logo_url': mentorship_service.logo_url,
                'duration': mentorship_service.duration,
                'language': mentorship_service.language,
                'allow_mentee_to_extend': mentorship_service.allow_mentee_to_extend,
                'allow_mentors_to_extend': mentorship_service.allow_mentors_to_extend,
                'max_duration': mentorship_service.max_duration,
                'missed_meeting_duration': mentorship_service.missed_meeting_duration,
                'created_at': mentorship_service.created_at,
                'updated_at': mentorship_service.updated_at,
                'description': mentorship_service.description,
            },
            'status': mentor_profile.status,
            'price_per_hour': mentor_profile.price_per_hour,
            'booking_url': mentor_profile.booking_url,
            'online_meeting_url': mentor_profile.online_meeting_url,
            'timezone': mentor_profile.timezone,
            'syllabus': [],
            'email': mentor_profile.email,
            'created_at': mentor_profile.created_at,
            'updated_at': mentor_profile.updated_at,
        },
        'mentee': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        },
    }


def render_session(mentorship_session,
                   mentor_profile,
                   user,
                   mentorship_service,
                   academy,
                   token,
                   fix_logo=False):
    request = None

    data = {
        'subject':
        mentorship_session.service.name,
        'room_url':
        mentorship_session.online_meeting_url,
        'session':
        get_mentorship_session_serializer(mentorship_session, mentor_profile, user, mentorship_service,
                                          academy),
        'userName': (token.user.first_name + ' ' + token.user.last_name).strip(),
        'backup_room_url':
        mentorship_session.mentor.online_meeting_url,
    }

    if token.user.id == mentorship_session.mentor.user.id:
        data['leave_url'] = '/mentor/session/' + str(mentorship_session.id) + '?token=' + token.key
    else:
        data['leave_url'] = 'close'

    string = loader.render_to_string('daily.html', data, request)

    if fix_logo:
        string = string.replace('src="/static/icons/picture.png"', 'src="/static/assets/icon.png"')

    return string


class AuthenticateTestSuite(MentorshipTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    def test_without_auth(self):
        url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                           kwargs={
                               'mentor_slug': 'asd',
                               'service_slug': 'asd'
                           })
        response = self.client.get(url)

        hash = self.bc.format.to_base64('/mentor/meet/asd/service/asd')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={hash}')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_without_mentor_profile(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                           kwargs={
                               'mentor_slug': 'asd',
                               'service_slug': 'asd'
                           }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f'No mentor found with slug asd')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_with_mentor_profile(self):
        model = self.bc.database.create(user=1, token=1, mentor_profile=1, mentorship_service=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                           kwargs={
                               'mentor_slug': model.mentor_profile.slug,
                               'service_slug': model.mentorship_service.slug
                           }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f'This mentor is not active at the moment',
                          model.mentor_profile,
                          model.token,
                          fix_logo=True)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
            self.bc.format.to_dict(model.mentor_profile),
        ])

    """
    🔽🔽🔽 GET without MentorProfile, bad statuses
    """

    def test_with_mentor_profile__bad_statuses(self):
        cases = [{'status': x} for x in ['INVITED', 'INNACTIVE']]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1,
                                            token=1,
                                            mentor_profile=mentor_profile,
                                            mentorship_service=1)

            querystring = self.bc.format.to_querystring({'token': model.token.key})
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(f'This mentor is not active at the moment',
                              model.mentor_profile,
                              model.token,
                              fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses without mentor urls
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock(side_effect=Exception()))
    def test_with_mentor_profile__good_statuses__without_mentor_urls(self):
        cases = [{'status': x} for x in ['ACTIVE', 'UNLISTED']]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1,
                                            token=1,
                                            mentor_profile=mentor_profile,
                                            mentorship_service=1)

            querystring = self.bc.format.to_querystring({'token': model.token.key})
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(f'This mentor is not ready too',
                              model.mentor_profile,
                              model.token,
                              fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, with mentee
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__good_statuses__with_mentor_urls__with_mentee(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1,
                                            token=1,
                                            mentor_profile=mentor_profile,
                                            mentorship_service=1)

            querystring = self.bc.format.to_querystring({'token': model.token.key})
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_session(model.mentor_profile,
                                           model.user,
                                           model.token,
                                           model.academy,
                                           model.mentorship_service,
                                           fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, with mentee of other user
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__good_statuses__with_mentor_urls__with_mentee__not_the_same_user(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        user = self.bc.database.create(user=1).user

        id = 0
        for args in cases:
            id += 1

            mentor_profile = {**args, 'user_id': 1}
            model = self.bc.database.create(user=1,
                                            token=1,
                                            mentor_profile=mentor_profile,
                                            mentorship_service=1)

            querystring = self.bc.format.to_querystring({'token': model.token.key})
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f'Hello {model.user.first_name} {model.user.last_name}, you are about to start a '
                f'{model.mentorship_service.name} with {user.first_name} {user.last_name}.',
                model.mentor_profile,
                model.token,
                fix_logo=True,
                start_session=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without_mentee__passing_session(
            self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        base = self.bc.database.create(user=1, token=1)

        id = 0
        for mentor_profile in cases:
            id += 1

            mentorship_session = {'mentee_id': None}
            model = self.bc.database.create(mentor_profile=mentor_profile,
                                            mentorship_session=mentorship_session,
                                            mentorship_service=1)

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring({
                'token': base.token.key,
                'session': model.mentorship_session.id,
            })
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_mentee(model.mentor_profile,
                                          base.user,
                                          base.token,
                                          model.academy,
                                          model.mentorship_service,
                                          fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without__passing_session__passing_mentee_does_not_exits(
            self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        base = self.bc.database.create(user=1, token=1)

        id = 0
        for mentor_profile in cases:
            id += 1

            mentorship_session = {'mentee_id': None}
            model = self.bc.database.create(mentor_profile=mentor_profile,
                                            mentorship_session=mentorship_session,
                                            mentorship_service=1)

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring({
                'token': base.token.key,
                'session': model.mentorship_session.id,
                'mentee': 10,
            })
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (f'/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?'
                   f'token={base.token.key}&session={model.academy.id}&mentee=10')
            expected = render(
                f'Mentee with user id 10 was not found, <a href="{url}&mentee=undefined">click '
                'here to start the session anyway.</a>',
                model.mentor_profile,
                base.token,
                fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee, MentorshipSession with bad status
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without__passing_session__passing_mentee__bad_status(
            self):
        mentor_cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        base = self.bc.database.create(user=1, token=1)

        id = 0
        for mentor_profile in mentor_cases:
            id += 1

            session_cases = [{
                'status': x,
                'mentee_id': None,
            } for x in ['COMPLETED', 'FAILED', 'IGNORED']]

            for mentorship_session in session_cases:
                base = self.bc.database.create(user=1, token=1)

                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                mentorship_service=1)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                querystring = self.bc.format.to_querystring({
                    'token': base.token.key,
                    'session': model.mentorship_session.id,
                    'mentee': base.user.id,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (f'/mentor/meet/{model.mentor_profile.slug}?token={base.token.key}&session='
                       f'{model.academy.id}&mentee=10')
                expected = render(
                    f'This mentoring session has ended ({model.mentorship_session.status}), would you like '
                    f'<a href="/mentor/meet/{model.mentor_profile.slug}">to start a new one?</a>.',
                    model.mentor_profile,
                    base.token,
                    fix_logo=True)

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__passing_session__passing_mentee__passing_redirect(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in cases:
            id += 1

            base = self.bc.database.create(user=1, token=1)

            mentorship_session = {'mentee_id': None}
            model = self.bc.database.create(mentor_profile=mentor_profile,
                                            mentorship_session=mentorship_session,
                                            mentorship_service=1)

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring({
                'token': base.token.key,
                'session': model.mentorship_session.id,
                'mentee': base.user.id,
                'redirect': 'true',
            })
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_session(model.mentorship_session,
                                      model.mentor_profile,
                                      base.user,
                                      model.mentorship_service,
                                      model.academy,
                                      base.token,
                                      fix_logo=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, user without name
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    def test_with_mentor_profile__without_user_name(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            mentorship_session = {'mentee_id': None}
            model = self.bc.database.create(mentor_profile=mentor_profile,
                                            mentorship_session=mentorship_session,
                                            user=user,
                                            mentorship_service=1)

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring({
                'token': base.token.key,
            })
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f'Hello student, you are about to start a {model.mentorship_service.name} with a mentor.',
                model.mentor_profile,
                base.token,
                fix_logo=True,
                start_session=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, with ends_at
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            ends_at = UTC_NOW - timedelta(seconds=10)
            mentorship_session = {'mentee_id': None, 'ends_at': ends_at}
            model = self.bc.database.create(mentor_profile=mentor_profile,
                                            mentorship_session=mentorship_session,
                                            user=user,
                                            mentorship_service=1)

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring({
                'token': base.token.key,
            })
            url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                               kwargs={
                                   'mentor_slug': model.mentor_profile.slug,
                                   'service_slug': model.mentorship_service.slug
                               }) + f'?{querystring}'
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (f'/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?'
                   f'token={base.token.key}&extend=true')
            expected = render(
                f'The mentoring session expired {timeago.format(ends_at, UTC_NOW)}: You can <a href="{url}">'
                'extend it for another 30 minutes</a> or end the session right now.',
                model.mentor_profile,
                base.token,
                mentorship_session=model.mentorship_session,
                fix_logo=True,
                session_expired=True)

            # dump error in external files
            if content != expected:
                with open('content.html', 'w') as f:
                    f.write(content)

                with open('expected.html', 'w') as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                self.bc.format.to_dict(model.mentor_profile),
            ])

            # teardown
            self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, with ends_at, with extend true
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.actions.extend_session', MagicMock(side_effect=lambda x: x))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true(self):
        mentor_profile_cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session_base = {'mentee_id': base.user.id, 'ends_at': ends_at}
            # session, token
            cases = [({
                **mentorship_session_base,
                'allow_mentors_to_extend': True,
            }, None), ({
                **mentorship_session_base,
                'allow_mentee_to_extend': True,
            }, 1)]

            for mentorship_session, token in cases:
                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                user=user,
                                                token=token,
                                                mentorship_service=1)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if 'token' in model else base.token

                querystring = self.bc.format.to_querystring({
                    'token': token.key,
                    'extend': 'true',
                    'mentee': base.user.id,
                    'session': model.mentorship_session.id,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)

                url = (
                    f'/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?'
                    f'token={token.key}&extend=true&mentee={base.user.id}&session={model.mentorship_session.id}'
                )
                expected = render(
                    f'The mentoring session expired {timeago.format(ends_at, UTC_NOW)}: You can '
                    f'<a href="{url}">extend it for another 30 minutes</a> or end the session right now.',
                    model.mentor_profile,
                    token,
                    mentorship_session=model.mentorship_session,
                    fix_logo=True,
                    session_expired=True)

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.actions.extend_session',
           MagicMock(side_effect=ExtendSessionException('xyz')))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__extend_session_raise_exception(self):
        mentor_profile_cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session = {'mentee_id': base.user.id, 'ends_at': ends_at}
            # session, token
            cases = [({
                'allow_mentors_to_extend': True,
            }, None), ({
                'allow_mentee_to_extend': True,
            }, 1)]

            for mentorship_service, token in cases:
                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                user=user,
                                                token=token,
                                                mentorship_service=mentorship_service)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if 'token' in model else base.token

                querystring = self.bc.format.to_querystring({
                    'token': token.key,
                    'extend': 'true',
                    'mentee': base.user.id,
                    'session': model.mentorship_session.id,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (f'/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&'
                       f'mentee={base.user.id}&session={model.mentorship_session.id}')
                expected = render('xyz',
                                  model.mentor_profile,
                                  token,
                                  mentorship_session=model.mentorship_session,
                                  fix_logo=True,
                                  session_expired=True)

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception,
    session can't be extended
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__session_can_not_be_extended(self):
        mentor_profile_cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session = {'mentee_id': base.user.id, 'ends_at': ends_at}
            # service, token
            cases = [
                ({
                    'allow_mentors_to_extend': False,
                    'allow_mentee_to_extend': False,
                }, None),
                ({
                    'allow_mentors_to_extend': False,
                    'allow_mentee_to_extend': False,
                }, 1),
            ]

            for mentorship_service, token in cases:
                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                user=user,
                                                token=token,
                                                mentorship_service=mentorship_service)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if 'token' in model else base.token

                querystring = self.bc.format.to_querystring({
                    'token': token.key,
                    'extend': 'true',
                    'mentee': base.user.id,
                    'session': model.mentorship_session.id,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (f'/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&'
                       f'mentee={base.user.id}&session={model.mentorship_session.id}')
                expected = render('The mentoring session expired 10 seconds ago and it cannot be extended.',
                                  model.mentor_profile,
                                  token,
                                  mentorship_session=model.mentorship_session,
                                  fix_logo=True)

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception, redirect
    to session
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__redirect_to_session(self):
        mentor_profile_cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {'first_name': '', 'last_name': ''}
            base = self.bc.database.create(user=user, token=1)

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            mentorship_session_base = {'mentee_id': base.user.id, 'ends_at': ends_at}
            # session, token
            cases = [({
                **mentorship_session_base,
                'allow_mentors_to_extend': True,
            }, None), ({
                **mentorship_session_base,
                'allow_mentee_to_extend': True,
            }, 1)]

            for mentorship_session, token in cases:
                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                user=user,
                                                token=token,
                                                mentorship_service=1)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if 'token' in model else base.token

                querystring = self.bc.format.to_querystring({
                    'token': token.key,
                    'extend': 'true',
                    'mentee': base.user.id,
                    'session': model.mentorship_session.id,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (f'/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&'
                       f'mentee={base.user.id}&session={model.mentorship_session.id}')
                expected = ''

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
                minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
                message = (
                    f'You have a session that expired {expired_at}. Only sessions with less than '
                    f'{minutes}min from expiration can be extended (if allowed by the academy)').replace(
                        ' ', '%20')
                self.assertEqual(
                    response.url, f'/mentor/session/{model.mentorship_session.id}?token='
                    f'{token.key}&message={message}')
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')

    """
    🔽🔽🔽 GET mock get_pending_sessions_or_create to get a empty queryset
    """

    @patch('breathecode.mentorship.actions.mentor_is_ready', MagicMock())
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'DAILY_API_URL': URL,
               'DAILY_API_KEY': API_KEY,
           })))
    @patch('requests.request',
           apply_requests_request_mock([(201, f'{URL}/v1/rooms', {
               'name': ROOM_NAME,
               'url': ROOM_URL,
           })]))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.actions.get_pending_sessions_or_create',
           MagicMock(side_effect=get_empty_mentorship_session_queryset))
    def test_get_pending_sessions_or_create_returns_empty_queryset(self):
        cases = [{
            'status': x,
            'online_meeting_url': self.bc.fake.url(),
            'booking_url': self.bc.fake.url(),
        } for x in ['ACTIVE', 'UNLISTED']]

        id = 0
        for mentor_profile in cases:
            id += 1

            first_name = self.bc.fake.first_name()
            last_name = self.bc.fake.last_name()
            cases = [
                ({
                    'first_name': '',
                    'last_name': ''
                }, 'the mentor'),
                ({
                    'first_name': first_name,
                    'last_name': last_name
                }, f'{first_name} {last_name}'),
            ]

            for user, name in cases:
                base = self.bc.database.create(user=user, token=1)

                ends_at = UTC_NOW - timedelta(seconds=10)
                mentorship_session = {'mentee_id': None, 'ends_at': ends_at}
                model = self.bc.database.create(mentor_profile=mentor_profile,
                                                mentorship_session=mentorship_session,
                                                user=user,
                                                mentorship_service=1)

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                querystring = self.bc.format.to_querystring({
                    'token': base.token.key,
                })
                url = reverse_lazy('mentorship_shortner:meet_slug_service_slug',
                                   kwargs={
                                       'mentor_slug': model.mentor_profile.slug,
                                       'service_slug': model.mentorship_service.slug
                                   }) + f'?{querystring}'
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = f'/mentor/meet/{model.mentor_profile.slug}?token={base.token.key}&extend=true'
                expected = render(f'Impossible to create or retrieve mentoring session with {name}.',
                                  model.mentor_profile,
                                  base.token,
                                  mentorship_session=model.mentorship_session,
                                  fix_logo=True)

                # dump error in external files
                if content != expected:
                    with open('content.html', 'w') as f:
                        f.write(content)

                    with open('expected.html', 'w') as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of('mentorship.MentorProfile'), [
                    self.bc.format.to_dict(model.mentor_profile),
                ])

                # teardown
                self.bc.database.delete('mentorship.MentorProfile')
