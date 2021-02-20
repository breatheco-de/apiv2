"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.authenticate.models import Token
from django.contrib.auth.models import User
from mixer.backend.django import mixer
from breathecode.tests.mixins import DateFormatterMixin

class AuthMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""
    password = 'pass1234'

    def generate_credentials(self, user=False, task=False, authenticate=False,
            manual_authenticate=False, cohort_user=False, profile_academy='',
            models={}, **kwargs):
        models = models.copy()

        if not 'user' in models and (user or authenticate or profile_academy or
                manual_authenticate or cohort_user or task):
            models['user'] = mixer.blend('auth.User')
            models['user'].set_password(self.password)
            models['user'].save()

        if authenticate:
            self.client.force_authenticate(user=models['user'])

        if manual_authenticate:
            token = Token.objects.create(user=models['user'])
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        return models
