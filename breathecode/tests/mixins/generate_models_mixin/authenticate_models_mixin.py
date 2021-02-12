"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.authenticate.models import (Capability, CredentialsFacebook, CredentialsGithub, CredentialsQuickBooks,
    Profile, ProfileAcademy, Role, Token, UserInvite, CredentialsSlack)
from mixer.backend.django import mixer
from breathecode.tests.mixins import DateFormatterMixin

class AuthenticateMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""
    password = 'pass1234'

    def generate_authenticate_models(self, profile_academy=False, capability='',
            role='', profile=False, user_invite=False, credentials_github=False,
            credentials_slack=False, credentials_facebook=False,
            credentials_quick_books=False, token=False,
            models={}, **kwargs):
        models = models.copy()

        if not 'profile' in models and profile:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            models['profile'] = mixer.blend('authenticate.Profile', **kargs)

        if not 'capability' in models and capability:
            kargs = {
                'slug': capability,
                'description': capability,
            }

            models['capability'] = mixer.blend('authenticate.Capability', **kargs)

        if not 'role' in models and role:
            kargs = {
                'slug': role,
                'name': role,
            }

            if capability:
                kargs['capabilities'] = [models['capability']]

            models['role'] = mixer.blend('authenticate.Role', **kargs)

        if not 'user_invite' in models and user_invite:
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = models['academy']

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            if 'role' in models:
                kargs['role'] = models['role']

            if 'author' in models:
                kargs['author'] = models['user']

            models['user_invite'] = mixer.blend('authenticate.UserInvite', **kargs)

        if not 'profile_academy' in models and profile_academy:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'role' in models:
                kargs['role'] = models['role']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            models['profile_academy'] = mixer.blend('authenticate.ProfileAcademy', **kargs)

        if not 'credentials_github' in models and credentials_github:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            models['credentials_github'] = mixer.blend('authenticate.CredentialsGithub', **kargs)

        if not 'credentials_slack' in models and credentials_slack:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            models['credentials_slack'] = mixer.blend('authenticate.CredentialsSlack', **kargs)

        if not 'credentials_facebook' in models and credentials_facebook:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            models['credentials_facebook'] = mixer.blend('authenticate.CredentialsFacebook', **kargs)

        if not 'credentials_quick_books' in models and credentials_quick_books:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            models['credentials_quick_books'] = mixer.blend('authenticate.CredentialsQuickBooks', **kargs)

        if not 'token' in models and token:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            models['token'] = mixer.blend('authenticate.Token', **kargs)

        return models
