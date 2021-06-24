"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from mixer.backend.django import mixer
from breathecode.tests.mixins import DateFormatterMixin


class AuthenticateMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""
    password = 'pass1234'

    def generate_authenticate_models(self,
                                     profile_academy=False,
                                     capability='',
                                     role='',
                                     profile=False,
                                     user_invite=False,
                                     credentials_github=False,
                                     credentials_slack=False,
                                     credentials_facebook=False,
                                     credentials_quick_books=False,
                                     token=False,
                                     device_id=False,
                                     profile_kwargs={},
                                     device_id_kwargs={},
                                     capability_kwargs={},
                                     role_kwargs={},
                                     user_invite_kwargs={},
                                     profile_academy_kwargs={},
                                     credentials_github_kwargs={},
                                     credentials_slack_kwargs={},
                                     credentials_facebook_kwargs={},
                                     credentials_quick_books_kwargs={},
                                     token_kwargs={},
                                     models={},
                                     **kwargs):
        models = models.copy()

        if not 'profile' in models and profile:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            kargs = {**kargs, **profile_kwargs}
            models['profile'] = mixer.blend('authenticate.Profile', **kargs)

        if not 'capability' in models and capability:
            kargs = {
                'slug': capability,
                'description': capability,
            }

            kargs = {**kargs, **capability_kwargs}
            models['capability'] = mixer.blend('authenticate.Capability',
                                               **kargs)

        if not 'role' in models and role:
            kargs = {
                'slug': role,
                'name': role,
            }

            if capability:
                kargs['capabilities'] = [models['capability']]

            kargs = {**kargs, **role_kwargs}
            models['role'] = mixer.blend('authenticate.Role', **kargs)

        if not 'user_invite' in models and user_invite:
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = models['academy']

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            if 'role' in models:
                kargs['role'] = models['role']

            if 'user' in models:
                kargs['author'] = models['user']

            kargs = {**kargs, **user_invite_kwargs}
            models['user_invite'] = mixer.blend('authenticate.UserInvite',
                                                **kargs)

        if not 'profile_academy' in models and profile_academy:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'role' in models:
                kargs['role'] = models['role']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **profile_academy_kwargs}
            models['profile_academy'] = mixer.blend(
                'authenticate.ProfileAcademy', **kargs)

        if not 'credentials_github' in models and credentials_github:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            kargs = {**kargs, **credentials_github_kwargs}
            models['credentials_github'] = mixer.blend(
                'authenticate.CredentialsGithub', **kargs)

        if not 'credentials_slack' in models and credentials_slack:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            kargs = {**kargs, **credentials_slack_kwargs}
            models['credentials_slack'] = mixer.blend(
                'authenticate.CredentialsSlack', **kargs)

        if not 'credentials_facebook' in models and credentials_facebook:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **credentials_facebook_kwargs}
            models['credentials_facebook'] = mixer.blend(
                'authenticate.CredentialsFacebook', **kargs)

        if not 'credentials_quick_books' in models and credentials_quick_books:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            kargs = {**kargs, **credentials_quick_books_kwargs}
            models['credentials_quick_books'] = mixer.blend(
                'authenticate.CredentialsQuickBooks', **kargs)

        if not 'token' in models and token:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            kargs = {**kargs, **token_kwargs}
            models['token'] = mixer.blend('authenticate.Token', **kargs)

        if not 'device_id' in models and device_id:
            kargs = {}

            kargs = {**kargs, **device_id_kwargs}
            models['device_id'] = mixer.blend('authenticate.DeviceId', **kargs)

        return models
