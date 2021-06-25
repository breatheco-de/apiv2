"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.authenticate.models import Capability, ProfileAcademy, Role, Token
from mixer.backend.django import mixer
from breathecode.tests.mixins import DateFormatterMixin


class AuthenticateMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""
    password = 'pass1234'

    def get_capability(self, id):
        return Capability.objects.filter(id=id).first()

    def get_role(self, id):
        return Role.objects.filter(id=id).first()

    def get_profile_academy(self, id):
        return ProfileAcademy.objects.filter(id=id).first()

    def get_capability_dict(self, id):
        data = Capability.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_role_dict(self, id):
        data = Role.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_profile_academy_dict(self, id):
        data = ProfileAcademy.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def all_capability_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Capability.objects.filter()
        ]

    def all_role_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Role.objects.filter()
        ]

    def all_profile_academy_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in ProfileAcademy.objects.filter()
        ]

    def generate_credentials(self,
                             profile_academy=False,
                             capability='',
                             role='',
                             models={},
                             external_models={}):
        self.maxDiff = None
        external_models = external_models.copy()
        models = models.copy()
        models = {}

        if (user or authenticate or profile_academy or manual_authenticate):
            models['user'] = mixer.blend('auth.User')
            models['user'].set_password(self.password)
            models['user'].save()

        if authenticate:
            self.client.force_authenticate(user=models['user'])

        if manual_authenticate:
            token = Token.objects.create(user=models['user'])
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        if not 'capability' in models and capability:
            kargs = {
                'slug': capability,
                'description': capability,
            }

            models['capability'] = mixer.blend('authenticate.Capability',
                                               **kargs)

        if not 'role' in models and role:
            kargs = {
                'slug': role,
                'name': role,
            }

            if capability:
                kargs['capabilities'] = [models['capability']]

            models['role'] = mixer.blend('authenticate.Role', **kargs)

        if not 'profile_academy' in models and profile_academy:
            kargs = {}

            if 'user' in external_models:
                kargs['user'] = external_models['user']

            if 'certificate' in external_models:
                kargs['certificate'] = external_models['certificate']

            if 'academy' in external_models:
                kargs['academy'] = external_models['academy']

            models['profile_academy'] = mixer.blend(
                'authenticate.ProfileAcademy', **kargs)

        return models
