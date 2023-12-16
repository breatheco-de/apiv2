"""
Test cases for /academy/:id/member/:id
"""
from datetime import timedelta
import os
import random
from unittest.mock import MagicMock, patch
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone

UTC_NOW = timezone.now()


def app_user_agreement_item(app, user, data={}):
    return {
        'agreed_at': UTC_NOW,
        'agreement_version': app.agreement_version,
        'app_id': app.id,
        'id': 0,
        'optional_scope_set_id': 0,
        'user_id': user.id,
        **data,
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message):
    request = None
    context = {
        'MESSAGE': message,
        'BUTTON': None,
        'BUTTON_TARGET': '_blank',
        'LINK': None,
        'BUTTON': 'Continue to 4Geeks',
        'LINK': os.getenv('APP_URL', '')
    }

    return loader.render_to_string('message.html', context, request)


def render_authorization(app, required_scopes=[], optional_scopes=[], selected_scopes=[], new_scopes=[]):
    environ = {
        'HTTP_COOKIE': '',
        'PATH_INFO': f'/',
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
        'QUERY_STRING': f'token=',
        'CONTENT_TYPE': 'application/octet-stream'
    }

    # if post:
    #     environ['REQUEST_METHOD'] = 'POST'
    #     environ['CONTENT_TYPE'] = 'multipart/form-data; boundary=BoUnDaRyStRiNg; charset=utf-8'

    request = WSGIRequest(environ)

    return loader.render_to_string(
        'authorize.html', {
            'app': app,
            'required_scopes': required_scopes,
            'optional_scopes': optional_scopes,
            'selected_scopes': selected_scopes,
            'new_scopes': new_scopes,
            'reject_url': app.redirect_url + '?app=4geeks&status=rejected',
        }, request)


class GetTestSuite(AuthTestCase):
    # When: no auth
    # Then: return 302
    def test_no_auth(self):
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': 'x'})
        response = self.client.get(url)

        hash = self.bc.format.to_base64('/v1/auth/authorize/x')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={hash}')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [])

    # When: app not found
    # Then: return 404
    def test_app_not_found(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': 'x'}) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('App not found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [])

    # When: app does not require an agreement
    # Then: return 404
    def test_app_does_not_require_an_agreement(self):
        app = {'require_an_agreement': False}
        model = self.bc.database.create(user=1, token=1, app=app)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('App not found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            self.bc.format.to_dict(model.app),
        ])

    # When: app require an agreement
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    def test_app_require_an_agreement(self):
        app = {'require_an_agreement': True}
        model = self.bc.database.create(user=1, token=1, app=app)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_authorization(model.app)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            self.bc.format.to_dict(model.app),
        ])

        self.assertTrue('permissions' not in content)
        self.assertTrue('required' not in content)
        self.assertTrue('optional' not in content)
        self.assertTrue(content.count('checked') == 0)
        self.assertTrue(content.count('New') == 0)

    # When: app require an agreement, with scopes
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    def test_app_require_an_agreement__with_scopes(self):
        app = {'require_an_agreement': True}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]
        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_authorization(model.app,
                                        required_scopes=[model.scope[0], model.scope[1]],
                                        optional_scopes=[model.scope[0], model.scope[1]],
                                        new_scopes=[])

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            self.bc.format.to_dict(model.app),
        ])

        self.assertTrue('permissions' in content)
        self.assertTrue('required' in content)
        self.assertTrue('optional' in content)
        self.assertTrue(content.count('checked') == 4)
        self.assertTrue(content.count('New') == 0)

    # When: app require an agreement, with scopes, it requires update the agreement
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    def test_app_require_an_agreement__with_scopes__updating_agreement(self):
        app = {'require_an_agreement': True}
        optional_scope_set = {'optional_scopes': [1]}
        # import timezone from django

        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_user_agreement = {'agreed_at': now + timedelta(days=1)}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_user_agreement=app_user_agreement,
                                        optional_scope_set=optional_scope_set,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_authorization(model.app,
                                        required_scopes=[model.scope[0], model.scope[1]],
                                        optional_scopes=[model.scope[0], model.scope[1]],
                                        selected_scopes=[model.scope[0].slug],
                                        new_scopes=[])

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            self.bc.format.to_dict(model.app),
        ])

        self.assertTrue('permissions' in content)
        self.assertTrue('required' in content)
        self.assertTrue('optional' in content)
        self.assertTrue(content.count('checked') == 3)
        self.assertTrue(content.count('New') == 0)

    # When: app require an agreement, with scopes, it requires update the agreement
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    def test_app_require_an_agreement__with_scopes__updating_agreement____(self):
        app = {'require_an_agreement': True}
        optional_scope_set = {'optional_scopes': []}
        # import timezone from django

        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_user_agreement = {'agreed_at': now - timedelta(days=1)}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_user_agreement=app_user_agreement,
                                        optional_scope_set=optional_scope_set,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_authorization(model.app,
                                        required_scopes=[model.scope[0], model.scope[1]],
                                        optional_scopes=[model.scope[0], model.scope[1]],
                                        selected_scopes=[],
                                        new_scopes=[model.scope[0].slug, model.scope[1].slug])

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            self.bc.format.to_dict(model.app),
        ])

        self.assertTrue('permissions' in content)
        self.assertTrue('required' in content)
        self.assertTrue('optional' in content)
        self.assertTrue(content.count('checked') == 4)
        self.assertTrue(content.count('New</span>') == 4)


class PostTestSuite(AuthTestCase):
    # When: no auth
    # Then: return 302
    def test_no_auth(self):
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': 'x'})
        response = self.client.post(url)

        hash = self.bc.format.to_base64('/v1/auth/authorize/x')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={hash}')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [])

    # When: app not found
    # Then: return 404
    def test_app_not_found(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': 'x'}) + f'?{querystring}'
        response = self.client.post(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('App not found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [])

    # When: app does not require an agreement
    # Then: return 404
    def test_app_does_not_require_an_agreement(self):
        app = {'require_an_agreement': False, 'agreement_version': 1}
        model = self.bc.database.create(user=1, token=1, app=app)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'
        response = self.client.post(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('App not found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            {
                **self.bc.format.to_dict(model.app),
                'agreement_version': 1,
            },
        ])

    # When: user without agreement
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_user_without_agreement(self):
        app = {'require_an_agreement': True, 'agreement_version': 1}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]
        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'

        data = {
            slug1: 'on',
            slug2: 'on',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.url, model.app.redirect_url + '?app=4geeks&status=authorized')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            {
                **self.bc.format.to_dict(model.app),
                'agreement_version': 1,
            },
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.AppUserAgreement'), [
            app_user_agreement_item(model.app, model.user, data={
                'id': 1,
                'optional_scope_set_id': 1,
            }),
        ])

    # When: user with agreement, scopes not changed
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_user_with_agreement__scopes_not_changed(self):
        app = {'require_an_agreement': True, 'agreement_version': 1}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]
        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_user_agreement = {'agreement_version': 1}

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes,
                                        app_user_agreement=app_user_agreement)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'

        data = {
            slug1: 'on',
            slug2: 'on',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.url, model.app.redirect_url + '?app=4geeks&status=authorized')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            {
                **self.bc.format.to_dict(model.app),
                'agreement_version': 1,
            },
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.AppUserAgreement'), [
            self.bc.format.to_dict(model.app_user_agreement),
        ])

    # When: user with agreement, scopes changed
    # Then: return 200
    @patch('django.template.context_processors.get_token', MagicMock(return_value='predicabletoken'))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_user_with_agreement__scopes_changed(self):
        app = {'require_an_agreement': True, 'agreement_version': 1}

        slug1 = self.bc.fake.slug().replace('-', '_')[:7]
        slug2 = self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug1 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        if random.randint(0, 1):
            slug2 += ':' + self.bc.fake.slug().replace('-', '_')[:7]

        scopes = [{'slug': slug1}, {'slug': slug2}]
        now = timezone.now()
        app_required_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        app_optional_scopes = [{'app_id': 1, 'scope_id': n + 1, 'agreed_at': now} for n in range(2)]
        optional_scope_set = {'optional_scopes': [1]}
        app_user_agreement = {'agreement_version': 1}

        model = self.bc.database.create(user=1,
                                        token=1,
                                        app=app,
                                        scope=scopes,
                                        app_required_scope=app_required_scopes,
                                        app_optional_scope=app_optional_scopes,
                                        app_user_agreement=app_user_agreement,
                                        optional_scope_set=optional_scope_set)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('authenticate:authorize_slug', kwargs={'app_slug': model.app.slug
                                                                  }) + f'?{querystring}'

        data = {
            slug1: 'on',
            slug2: 'on',
        }
        response = self.client.post(url, data)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.url, model.app.redirect_url + '?app=4geeks&status=authorized')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.App'), [
            {
                **self.bc.format.to_dict(model.app),
                'agreement_version': 1,
            },
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.AppUserAgreement'), [
            {
                **self.bc.format.to_dict(model.app_user_agreement),
                'agreed_at': UTC_NOW,
                'optional_scope_set_id': 2,
                'agreement_version': 1,
            },
        ])
