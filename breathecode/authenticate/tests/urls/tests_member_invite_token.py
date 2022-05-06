"""
Test cases for /academy/:id/member/:id
"""
import os
from django.core.handlers.wsgi import WSGIRequest
from unittest.mock import MagicMock, patch
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from django.http.request import HttpRequest
from random import randint
from breathecode.authenticate.forms import InviteForm
from ..mixins.new_auth_test_case import AuthTestCase

CSRF_TOKEN = str(randint(10000, 10000000000000))
render_to_string = loader.render_to_string


class Message(str):
    tags: str

    def __init__(self, css_class, *_):
        self.tags = css_class
        return super().__init__()

    def __new__(cls, _, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)


# IMPORTANT: the loader.render_to_string in a function is inside of funcion render
def render_page_without_invites():
    request = None
    APP_URL = os.getenv('APP_URL', '')

    return loader.render_to_string(
        'message.html', {
            'MESSAGE': 'Invitation not found with this token or it was already accepted',
            'BUTTON': None,
            'BUTTON_TARGET': '_blank',
            'LINK': None,
        }, request)


def render_page_with_user_invite(model, arguments={}):
    environ = {
        'HTTP_COOKIE': '',
        'PATH_INFO': f'/v1/auth/member/invite/{model.user_invite.token}',
        'REMOTE_ADDR': '127.0.0.1',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': {},
        'wsgi.errors': {},
        'wsgi.multiprocess': True,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'QUERY_STRING': '',
        'CONTENT_TYPE': 'application/octet-stream'
    }
    request = WSGIRequest(environ)

    data = {'callback': [''], 'token': [model.user_invite.token], **arguments}
    form = InviteForm({
        **data,
        'first_name': model.user_invite.first_name,
        'last_name': model.user_invite.last_name,
        'phone': model.user_invite.phone,
    })

    return loader.render_to_string('form_invite.html', {'form': form, 'csrf_token': CSRF_TOKEN}, request)


def render_page_post_form(token, arguments={}, messages=[]):
    request = HttpRequest()
    environ = {
        'HTTP_COOKIE': '',
        'PATH_INFO': f'/v1/auth/member/invite/{token}',
        'REMOTE_ADDR': '127.0.0.1',
        'REQUEST_METHOD': 'POST',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': {},
        'wsgi.errors': {},
        'wsgi.multiprocess': True,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'QUERY_STRING': '',
        'CONTENT_TYPE': 'multipart/form-data; boundary=BoUnDaRyStRiNg; charset=utf-8'
    }
    request = WSGIRequest(environ)

    data = {'callback': '', 'token': token, **arguments}
    form = InviteForm(data)

    context = {
        'form': form,
        'csrf_token': CSRF_TOKEN,
    }

    if messages:
        context['messages'] = messages

    return loader.render_to_string('form_invite.html', context, request)


def render_page_post_successfully():
    request = None

    return loader.render_to_string('message.html', {
        'MESSAGE': 'Welcome to 4Geeks, you can go ahead an log in',
    }, request)


def render_to_string_mock(*args, **kwargs):
    new_args = list(args)
    base = new_args[1] if new_args[1] else {}
    new_args[1] = {**base, 'csrf_token': CSRF_TOKEN}
    return render_to_string(*new_args, **kwargs)


class GetHasherMock:
    def __init__(self, *args, **kwargs):
        ...

    def encode(self, password, salt):
        return CSRF_TOKEN

    def salt(self):
        return 'salt'


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 GET without UserInvite
    """
    def test_member_invite_token__without_user_invite(self):
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': 'invalid'})
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_without_invites()

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])

    """
    🔽🔽🔽 GET with UserInvite
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    def test_member_invite_token__with_user_invite(self):
        model = self.bc.database.create(user_invite=1)

        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_user_invite(model)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

    """
    🔽🔽🔽 POST bad token, UserInvite without email
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    def test_member_invite_token__post__bad_token(self):
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': 'invalid'})
        data = {}
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_form(
            token='invalid',
            messages=[Message('alert-danger', 'Invalid or expired invitation invalid')],
            arguments={})

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.User'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST bad first and last name, UserInvite with email
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    def test_member_invite_token__post__bad_first_and_last_name(self):
        user_invite = {'email': 'user@dotdotdotdot.dot'}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {}
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_form(token=model.user_invite.token,
                                         messages=[Message('alert-danger', 'Invalid first or last name')],
                                         arguments={})

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST password is empty, UserInvite with email
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__password_is_empty(self):
        user_invite = {'email': 'user@dotdotdotdot.dot'}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {'first_name': 'abc', 'last_name': 'xyz'}
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_form(token=model.user_invite.token,
                                         messages=[Message('alert-danger', 'Password is empty')],
                                         arguments=data)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST passwords doesn't not match, UserInvite with email
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__passwords_does_not_match(self):
        user_invite = {'email': 'user@dotdotdotdot.dot'}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp1',
            'password2': '^3^3uUppppp2',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_form(token=model.user_invite.token,
                                         messages=[Message('alert-danger', "Passwords don't match")],
                                         arguments=data)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite with email
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_first_name_last_name_and_passwords(self):
        user_invite = {'email': 'user@dotdotdotdot.dot'}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_successfully()

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             **self.bc.format.to_dict(model.user_invite),
                             'status': 'ACCEPTED',
                         }])

        user_db = [
            x for x in self.bc.database.list_of('authenticate.User')
            if x['date_joined'] and x.pop('date_joined')
        ]
        self.assertEqual(user_db, [{
            'email': 'user@dotdotdotdot.dot',
            'first_name': 'abc',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'xyz',
            'password': CSRF_TOKEN,
            'username': 'user@dotdotdotdot.dot'
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite with email, providing callback url
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_first_name_last_name_and_passwords__with_callback(self):
        user_invite = {'email': 'user@dotdotdotdot.dot'}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
            'callback': '/1337'
        }
        response = self.client.post(url, data, format='multipart')

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, '/1337')
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             **self.bc.format.to_dict(model.user_invite),
                             'status': 'ACCEPTED',
                         }])

        user_db = [
            x for x in self.bc.database.list_of('authenticate.User')
            if x['date_joined'] and x.pop('date_joined')
        ]
        self.assertEqual(user_db, [{
            'email': 'user@dotdotdotdot.dot',
            'first_name': 'abc',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': 'xyz',
            'password': CSRF_TOKEN,
            'username': 'user@dotdotdotdot.dot'
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite and User with email and ProfileAcademy
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_first_name_last_name_and_passwords__with_profile_academy(self):
        user = {'email': 'user@dotdotdotdot.dot', 'first_name': 'Lord', 'last_name': 'Valdomero'}
        model = self.bc.database.create(user=user, user_invite=user, profile_academy=user, role='reviewer')
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_successfully()

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             **self.bc.format.to_dict(model.user_invite),
                             'status': 'ACCEPTED',
                         }])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [
            self.bc.format.to_dict(model.user),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             **self.bc.format.to_dict(model.profile_academy),
                             'first_name': model.user.first_name,
                             'last_name': model.user.last_name,
                             'status': 'ACTIVE',
                         }])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'REVIEWER',
            'user_id': 1
        }])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite and User with email and Cohort
    with Role
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_cohort__with_role(self):
        user = {'email': 'user@dotdotdotdot.dot', 'first_name': 'Lord', 'last_name': 'Valdomero'}
        model = self.bc.database.create(user=user, user_invite=user, cohort=1, role=1)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_successfully()

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             **self.bc.format.to_dict(model.user_invite),
                             'status': 'ACCEPTED',
                         }])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [
            self.bc.format.to_dict(model.user),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': model.role.slug.upper(),
            'user_id': 1,
        }])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite and User with email and Cohort
    with Role
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_cohort__without_role_in_the_invite__role_student_exists(self):
        user = {'email': 'user@dotdotdotdot.dot', 'first_name': 'Lord', 'last_name': 'Valdomero'}
        user_invite = {**user, 'role_id': None}
        model = self.bc.database.create(user=user, user_invite=user_invite, cohort=1, role='student')
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_successfully()

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'),
                         [{
                             **self.bc.format.to_dict(model.user_invite),
                             'status': 'ACCEPTED',
                         }])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [
            self.bc.format.to_dict(model.user),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'student',
            'user_id': 1,
        }])

    """
    🔽🔽🔽 POST with first name, last name and passwords, UserInvite and User with email and Cohort
    without Role in the invite and Role student not exists
    """

    @patch('django.template.loader.render_to_string', MagicMock(side_effect=render_to_string_mock))
    @patch('django.contrib.auth.hashers.get_hasher', MagicMock(side_effect=GetHasherMock))
    def test_member_invite_token__post__with_cohort__without_role(self):
        user = {'email': 'user@dotdotdotdot.dot', 'first_name': 'Lord', 'last_name': 'Valdomero'}
        model = self.bc.database.create(user=user, user_invite=user, cohort=1)
        url = reverse_lazy('authenticate:member_invite_token', kwargs={'token': model.user_invite.token})
        data = {
            'first_name': 'abc',
            'last_name': 'xyz',
            'password1': '^3^3uUppppp',
            'password2': '^3^3uUppppp',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_post_form(
            token=model.user_invite.token,
            messages=[
                Message('alert-danger',
                        'Unexpected error occurred with invite, please contact the staff of 4geeks')
            ],
            arguments=data)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [
            self.bc.format.to_dict(model.user_invite),
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [
            self.bc.format.to_dict(model.user),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
