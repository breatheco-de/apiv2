"""
Test cases for /user
"""
import re
import urllib
from unittest import mock

import pytest
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

from ...models import Role
from ..mixins.new_auth_test_case import AuthTestCase
from ..mocks import GithubRequestsMock


class ResponseMock:

    def __init__(self, status_code):
        self.status_code = status_code


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):

    get_routes = {
        'https://api.github.com/user': GithubRequestsMock.user(),
        'https://api.github.com/user/emails': GithubRequestsMock.user_emails(),
    }

    post_routes = {
        'https://github.com/login/oauth/access_token': GithubRequestsMock.access_token(),
        'https://rigobot.herokuapp.com/v1/auth/invite': ResponseMock(200),
    }

    def get_patch(url, *args, **kwargs):
        return get_routes.get(url)

    def post_patch(url, *args, **kwargs):
        return post_routes.get(url)

    monkeypatch.setattr('requests.get', get_patch)
    monkeypatch.setattr('requests.post', post_patch)

    yield


def render(message):
    request = None
    return loader.render_to_string(
        'message.html',
        {
            'MESSAGE': message,
            'BUTTON': None,
            'BUTTON_TARGET': '_blank',
            'LINK': None
        },
        request,
        using=None,
    )


def get_profile_fields(data={}):
    return {
        'id': 1,
        'user_id': 1,
        'avatar_url': 'https://avatars2.githubusercontent.com/u/3018142?v=4',
        'bio':
        'I am an Computer engineer, Full-stack Developer\xa0and React Developer, I likes an API good, the clean code, the good programming practices',
        'phone': '',
        'show_tutorial': True,
        'twitter_username': None,
        'github_username': None,
        'portfolio_url': None,
        'linkedin_url': None,
        'blog': 'https://www.facebook.com/chocoland.framework',
        **data,
    }


def get_credentials_github_fields(data={}):
    bio = ('I am an Computer engineer, Full-stack Developer\xa0and React '
           'Developer, I likes an API good, the clean code, the good programming '
           'practices')
    return {
        'avatar_url': 'https://avatars2.githubusercontent.com/u/3018142?v=4',
        'bio': bio,
        'blog': 'https://www.facebook.com/chocoland.framework',
        'company': '@chocoland ',
        'email': 'jdefreitaspinto@gmail.com',
        'github_id': 3018142,
        'name': 'Jeferson De Freitas',
        'token': 'e72e16c7e42f292c6912e7710c838347ae178b4a',
        'twitter_username': None,
        'user_id': 1,
        'username': 'jefer94',
        **data,
    }


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__without_code(bc: Breathecode, client: APIClient):
    """Test /github/callback without auth"""
    url = reverse_lazy('authenticate:github_callback')
    params = {'url': 'https://google.co.ve'}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    data = response.json()
    expected = {'detail': 'no-code', 'status_code': 400}

    assert data == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of('auth.User') == []
    assert bc.database.list_of('authenticate.Profile') == []
    assert bc.database.list_of('authenticate.CredentialsGithub') == []
    assert bc.database.list_of('authenticate.ProfileAcademy') == []


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__user_not_exist(bc: Breathecode, client: APIClient):
    """Test /github/callback"""

    original_url_callback = 'https://google.co.ve'
    code = 'Konan'

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code}

    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')
    content = bc.format.from_bytes(response.content)
    expected = render('We could not find in our records the email associated to this github account, '
                      'perhaps you want to signup to the platform first? <a href="' + original_url_callback +
                      '">Back to 4Geeks.com</a>')

    # dump error in external files
    if content != expected:
        with open('content.html', 'w') as f:
            f.write(content)

        with open('expected.html', 'w') as f:
            f.write(expected)

    assert content == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of('auth.User') == []
    assert bc.database.list_of('authenticate.Profile') == []
    assert bc.database.list_of('authenticate.CredentialsGithub') == []
    assert bc.database.list_of('authenticate.ProfileAcademy') == []


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__user_not_exist_but_waiting_list(bc: Breathecode, client: APIClient):
    """Test /github/callback"""

    user_invite = {'status': 'WAITING_LIST', 'email': 'jdefreitaspinto@gmail.com'}
    bc.database.create(user_invite=user_invite)

    original_url_callback = 'https://google.co.ve'
    code = 'Konan'

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code}

    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')
    content = bc.format.from_bytes(response.content)
    expected = render('You are still number 1 on the waiting list, we will email you once you are given access '
                      f'<a href="{original_url_callback}">Back to 4Geeks.com</a>')

    # dump error in external files
    if content != expected:
        with open('content.html', 'w') as f:
            f.write(content)

        with open('expected.html', 'w') as f:
            f.write(expected)

    assert content == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of('auth.User') == []
    assert bc.database.list_of('authenticate.Profile') == []
    assert bc.database.list_of('authenticate.CredentialsGithub') == []
    assert bc.database.list_of('authenticate.ProfileAcademy') == []


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == []
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user__with_email_in_uppercase(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [get_profile_fields(data={})]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == []


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_bad_user_in_querystring(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=True,
                               user=True,
                               profile_academy=True,
                               user_kwargs=user_kwargs,
                               role_kwargs=role_kwargs,
                               token=True)

    original_url_callback = 'https://google.co.ve'
    code = 'Konan'

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': 'b14f'}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')
    json = response.json()
    expected = {'detail': 'token-not-found', 'status_code': 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]
    assert bc.database.list_of('authenticate.Profile') == []
    assert bc.database.list_of('authenticate.CredentialsGithub') == []
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=True,
                               user=True,
                               profile_academy=True,
                               user_kwargs=user_kwargs,
                               role_kwargs=role_kwargs,
                               token=True)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [get_profile_fields(data={})]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user__profile_without_avatar_url(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=True,
                               user=True,
                               profile_academy=True,
                               user_kwargs=user_kwargs,
                               role_kwargs=role_kwargs,
                               profile=1,
                               token=True)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [
        get_profile_fields(data={
            'bio': None,
            'blog': None
        }),
    ]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user__profile_with_avatar_url(bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
    role_kwargs = {'slug': 'student', 'name': 'Student'}
    profile = {'avatar_url': bc.fake.url()}
    model = bc.database.create(role=True,
                               user=True,
                               profile_academy=True,
                               user_kwargs=user_kwargs,
                               role_kwargs=role_kwargs,
                               profile=profile,
                               token=True)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [
        get_profile_fields(data={
            'bio': None,
            'blog': None,
            **profile
        }),
    ]

    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user_different_email__without_credetials_of_github__without_cohort_user(
        bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user = {'email': 'FJOSE123@GMAIL.COM'}
    role = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=role, user=user, profile_academy=True, token=True)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [get_profile_fields(data={})]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user_different_email__without_credetials_of_github__with_cohort_user(
        bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    user = {'email': 'FJOSE123@GMAIL.COM'}
    role = {'slug': 'student', 'name': 'Student'}
    model = bc.database.create(role=role, user=user, profile_academy=True, cohort_user=1, token=True)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of('authenticate.Profile') == [get_profile_fields(data={})]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user_different_email__with_credentials_of_github__without_cohort_user(
        bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    users = [{'email': 'FJOSE123@GMAIL.COM'}, {'email': 'jdefreitaspinto@gmail.com'}]
    role = {'slug': 'student', 'name': 'Student'}
    credentials_github = {'github_id': 3018142}
    token = {'user_id': 2}
    model = bc.database.create(role=role,
                               user=users,
                               profile_academy=True,
                               credentials_github=credentials_github,
                               token=token)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == bc.format.to_dict(model.user)

    assert bc.database.list_of('authenticate.Profile') == [
        get_profile_fields(data={'user_id': 2}),
    ]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(data={'user_id': 2}),
    ]
    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy),
    ]


@mock.patch('django.db.models.signals.pre_delete.send', mock.MagicMock(return_value=None))
@mock.patch('breathecode.admissions.signals.student_edu_status_updated.send', mock.MagicMock(return_value=None))
def test_github_callback__with_user_different_email__with_credentials_of_github__with_cohort_user(
        bc: Breathecode, client: APIClient):
    """Test /github/callback"""
    users = [{'email': 'FJOSE123@GMAIL.COM'}, {'email': 'jdefreitaspinto@gmail.com'}]
    role = {'slug': 'student', 'name': 'Student'}
    credentials_github = {'github_id': 3018142}
    token = {'user_id': 2}
    cohort_user = {'user_id': 2}
    model = bc.database.create(role=role,
                               user=users,
                               cohort_user=cohort_user,
                               profile_academy=True,
                               credentials_github=credentials_github,
                               token=token)

    original_url_callback = 'https://google.co.ve'
    token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') + r'\?token=[0-9a-zA-Z]{,40}$')
    code = 'Konan'

    token = model.token

    url = reverse_lazy('authenticate:github_callback')
    params = {'url': original_url_callback, 'code': code, 'user': token}
    response = client.get(f'{url}?{urllib.parse.urlencode(params)}')

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of('auth.User') == bc.format.to_dict(model.user)

    assert bc.database.list_of('authenticate.Profile') == [
        get_profile_fields(data={'user_id': 2}),
    ]
    assert bc.database.list_of('authenticate.CredentialsGithub') == [
        get_credentials_github_fields(data={'user_id': 2}),
    ]

    assert bc.database.list_of('authenticate.ProfileAcademy') == [
        bc.format.to_dict(model.profile_academy), {
            'academy_id': 1,
            'address': None,
            'email': 'jdefreitaspinto@gmail.com',
            'first_name': model.user[1].first_name,
            'id': 2,
            'last_name': model.user[1].last_name,
            'phone': '',
            'role_id': 'student',
            'status': 'ACTIVE',
            'user_id': 2
        }
    ]
