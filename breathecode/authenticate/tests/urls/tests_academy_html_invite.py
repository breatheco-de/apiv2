"""
Test cases for /academy/:id/member/:id
"""
import os
import urllib.parse
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


# IMPORTANT: the loader.render_to_string in a function is inside of funcion render
def render_page_without_invites():
    request = None
    APP_URL = os.getenv('APP_URL', '')

    return loader.render_to_string(
        'message.html', {
            'MESSAGE': f'You don\'t have any more pending invites',
            'BUTTON': 'Continue to 4Geeks',
            'BUTTON_TARGET': '_blank',
            'LINK': APP_URL
        }, request)


def render_page_with_pending_invites(model):
    request = None
    APP_URL = os.getenv('APP_URL', '')
    profile_academies = []
    if 'profile_academy' in model:
        profile_academies = model.profile_academy if isinstance(model.profile_academy,
                                                                list) else [model.profile_academy]

    # excluding the accepted invited
    profile_academies = [x for x in profile_academies if x.status != 'ACTIVE']

    querystr = urllib.parse.urlencode({'callback': APP_URL, 'token': model.token.key})
    url = os.getenv('API_URL') + '/v1/auth/academy/html/invite?' + querystr
    return loader.render_to_string(
        'academy_invite.html', {
            'subject':
            f'Invitation to study at 4Geeks.com',
            'invites': [{
                'id': profile_academy.id,
                'academy': {
                    'id': profile_academy.academy.id,
                    'name': profile_academy.academy.name,
                    'slug': profile_academy.academy.slug,
                    'timezone': profile_academy.academy.timezone,
                },
                'role': profile_academy.role.slug,
                'created_at': profile_academy.created_at,
            } for profile_academy in profile_academies],
            'LINK':
            url,
            'user': {
                'id': model.user.id,
                'email': model.user.email,
                'first_name': model.user.first_name,
            }
        }, request)


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    def test_academy_html_invite__without_auth(self):
        url = reverse_lazy('authenticate:academy_html_invite')
        response = self.client.get(url)

        hash = self.bc.format.to_base64('/v1/auth/academy/html/invite')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={hash}')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    """
    🔽🔽🔽 GET without ProfileAcademy
    """

    def test_academy_html_invite__without_profile_academy(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:academy_html_invite') + f'?{querystring}'
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    """
    🔽🔽🔽 GET with one ProfileAcademy
    """

    def test_academy_html_invite__with_one_profile_academy(self):
        model = self.bc.database.create(user=1, token=1, profile_academy=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:academy_html_invite') + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(model)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    """
    🔽🔽🔽 GET with two ProfileAcademy
    """

    def test_academy_html_invite__with_two_profile_academy(self):
        model = self.bc.database.create(user=1, token=1, profile_academy=2)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:academy_html_invite') + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(model)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         self.bc.format.to_dict(model.profile_academy))

    """
    🔽🔽🔽 GET with two ProfileAcademy, accepting both
    """

    def test_academy_html_invite__with_two_profile_academy__accepting_both(self):
        model = self.bc.database.create(user=1, token=1, profile_academy=2)

        querystring = self.bc.format.to_querystring({'token': model.token.key, 'accepting': '1,2'})
        url = reverse_lazy('authenticate:academy_html_invite') + f'?{querystring}'
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'),
                         [{
                             **self.bc.format.to_dict(profile_academy),
                             'status': 'ACTIVE',
                         } for profile_academy in model.profile_academy])

    """
    🔽🔽🔽 GET with two ProfileAcademy, rejecting both
    """

    def test_academy_html_invite__with_two_profile_academy__rejecting_both(self):
        model = self.bc.database.create(user=1, token=1, profile_academy=2)

        querystring = self.bc.format.to_querystring({'token': model.token.key, 'rejecting': '1,2'})
        url = reverse_lazy('authenticate:academy_html_invite') + f'?{querystring}'
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
