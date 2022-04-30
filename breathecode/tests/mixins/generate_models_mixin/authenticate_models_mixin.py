"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.tests.mixins import DateFormatterMixin
from .utils import is_valid, create_models, just_one, get_list


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

        if not 'profile' in models and is_valid(profile):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['profile'] = create_models(profile, 'authenticate.Profile', **{**kargs, **profile_kwargs})

        if not 'capability' in models and is_valid(capability):
            kargs = {
                'slug': capability,
                'description': capability,
            }

            models['capability'] = create_models(profile, 'authenticate.Capability', **{
                **kargs,
                **capability_kwargs
            })

        if not 'role' in models and (is_valid(role) or is_valid(profile_academy)):
            kargs = {
                'slug': role,
                'name': role,
            } if isinstance(role, str) else {}

            if capability:
                kargs['capabilities'] = get_list(models['capability'])

            models['role'] = create_models(role if not isinstance(role, str) else {}, 'authenticate.Role', **{
                **kargs,
                **role_kwargs
            })

        if not 'user_invite' in models and is_valid(user_invite):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            if 'role' in models:
                kargs['role'] = just_one(models['role'])

            if 'user' in models:
                kargs['author'] = just_one(models['user'])

            models['user_invite'] = create_models(user_invite, 'authenticate.UserInvite', **{
                **kargs,
                **user_invite_kwargs
            })

        if not 'profile_academy' in models and is_valid(profile_academy):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'role' in models:
                kargs['role'] = just_one(models['role'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['profile_academy'] = create_models(profile_academy, 'authenticate.ProfileAcademy', **{
                **kargs,
                **profile_academy_kwargs
            })

        if not 'credentials_github' in models and is_valid(credentials_github):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['credentials_github'] = create_models(credentials_github, 'authenticate.CredentialsGithub',
                                                         **{
                                                             **kargs,
                                                             **credentials_github_kwargs
                                                         })

        if not 'credentials_slack' in models and is_valid(credentials_slack):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['credentials_slack'] = create_models(credentials_slack, 'authenticate.CredentialsSlack',
                                                        **{
                                                            **kargs,
                                                            **credentials_slack_kwargs
                                                        })

        if not 'credentials_facebook' in models and is_valid(credentials_facebook):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['credentials_facebook'] = create_models(credentials_facebook,
                                                           'authenticate.CredentialsFacebook', **{
                                                               **kargs,
                                                               **credentials_facebook_kwargs
                                                           })

        if not 'credentials_quick_books' in models and is_valid(credentials_quick_books):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['credentials_quick_books'] = create_models(credentials_quick_books,
                                                              'authenticate.CredentialsQuickBooks', **{
                                                                  **kargs,
                                                                  **credentials_quick_books_kwargs
                                                              })

        if not 'token' in models and is_valid(token):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['token'] = create_models(token, 'authenticate.Token', **{**kargs, **token_kwargs})

        if not 'device_id' in models and is_valid(device_id):
            kargs = {}

            models['device_id'] = create_models(device_id, 'authenticate.DeviceId', **{
                **kargs,
                **device_id_kwargs
            })

        return models
