"""
Collections of mixins used to login in authorize microservice
"""
import os, re
from unittest.mock import patch
from urllib.parse import urlencode
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.assignments.models import PENDING, PROJECT
from breathecode.certificate.models import UserSpecialty
from .development_environment import DevelopmentEnvironment
from django.core.cache import cache
from ...models import Certificate, Cohort
from ..mocks import (GOOGLE_CLOUD_PATH, apply_google_cloud_client_mock,
                     apply_google_cloud_bucket_mock,
                     apply_google_cloud_blob_mock)


# class CertificateTestCase(TransactionTestCase, DevelopmentEnvironment):
class CertificateTestCase(APITestCase, DevelopmentEnvironment):
    """APITestCase with Certificate models"""
    token = '9e76a2ab3bd55454c384e0a5cdb5298d17285949'
    token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")
    preview_url_pattern = re.compile(
        "^https:\/\/storage\.cloud\.google\.com\/certificates-"
        "breathecode\/[0-9a-zA-Z]{,40}$")

    def check_all_token(self, models: dict):
        return [
            model for model in models
            if self.token_pattern.match(model['token']) and model.pop('token')
        ]

    def check_all_preview_url(self, models: dict):
        # return [model for model in models if "preview_url" in models and self.preview_url_pattern.match(model['preview_url'])]
        _models = []
        for model in models:
            if "preview_url" in model:
                model.pop(
                    "preview_url"
                )  # and self.preview_url_pattern.match(model['preview_url'])]
            _models.append(model)

        return _models

    def remove_model_state(self, dict):
        result = None
        if dict:
            result = dict.copy()
            del result['_state']
        return result

    def remove_created_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'created_at' in result:
                del result['created_at']
        return result

    def remove_updated_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'updated_at' in result:
                del result['updated_at']
        return result

    def remove_dinamics_fields(self, dict):
        return self.remove_updated_at(
            self.remove_model_state(self.remove_created_at(dict)))

    def model_to_dict(self, models: dict, key: str) -> dict:
        if key in models:
            return self.remove_dinamics_fields(models[key].__dict__)

    def count_cohort(self):
        return Cohort.objects.count()

    def count_certificate(self):
        return Certificate.objects.count()

    def count_user_specialty(self):
        return UserSpecialty.objects.count()

    def all_cohort_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Cohort.objects.filter()
        ]

    def all_certificate_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Certificate.objects.filter()
        ]

    def all_user_specialty_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in UserSpecialty.objects.filter()
        ]

    def all_model_dict(self, models: list[dict]):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in models
        ]

    def user_specialty_has_preview_url(self, certificate_id):
        """preview_url is set?"""
        certificate = UserSpecialty.objects.get(id=certificate_id)
        return certificate.preview_url is not None

    def generate_screenshotmachine_url(self, user_specialty):
        """Generate screenshotmachine url"""
        certificate = user_specialty
        query_string = urlencode({
            'key':
            os.environ.get('SCREENSHOT_MACHINE_KEY'),
            'url':
            f'https://certificate.breatheco.de/preview/{certificate.token}',
            'device':
            'desktop',
            'cacheLimit':
            '0',
            'dimension':
            '1024x707',
        })
        return f'https://api.screenshotmachine.com?{query_string}'

    def setUp(self):
        cache.clear()

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models(self,
                        language='',
                        stage=False,
                        teacher=False,
                        layout_design=False,
                        specialty=False,
                        finished=False,
                        finantial_status=None,
                        task=None,
                        cohort=False,
                        certificate=False,
                        teacher_user=False,
                        user_specialty=False,
                        user=False,
                        cohort_user=False,
                        models={}):
        """Generate models"""
        self.maxDiff = None
        models = models.copy()

        if not 'certificate' in models and (certificate or specialty or cohort
                                            or cohort_user or teacher):
            models['certificate'] = mixer.blend('admissions.Certificate')

        if not 'layout_design' in models and layout_design:
            models['layout_design'] = mixer.blend('certificate.LayoutDesign',
                                                  slug='default')

        if not 'specialty' in models and specialty:
            kargs = {}

            if certificate:
                kargs['certificate'] = models['certificate']

            models['specialty'] = mixer.blend('certificate.Specialty', **kargs)

        if not 'user_specialty' in models and user_specialty:
            models['user_specialty'] = mixer.blend(
                'certificate.UserSpecialty',
                token=self.token,
                preview_url="https://asdasd.com")

        if not 'user' in models and (user or cohort_user or task):
            models['user'] = mixer.blend('auth.User')

        if not 'task' in models and task:
            kargs = {
                'user': models['user'],
                'revision_status': PENDING,
                'task_type': PROJECT,
            }

            models['task'] = mixer.blend('assignments.Task', **kargs)

        if not 'cohort' in models and (cohort or cohort_user or teacher):
            kargs = {
                'certificate': models['certificate'],
            }

            if finished:
                kargs['current_day'] = models['certificate'].duration_in_days

            if stage:
                kargs['stage'] = 'ENDED'

            if language:
                kargs['language'] = language

            models['cohort'] = mixer.blend('admissions.Cohort', **kargs)

        if not 'cohort_user' in models and cohort_user:
            kargs = {
                'educational_status': 'GRADUATED',
                'user': models['user'],
                'cohort': models['cohort'],
            }

            if finantial_status:
                kargs['finantial_status'] = finantial_status

            models['cohort_user'] = mixer.blend('admissions.CohortUser',
                                                **kargs)

        if not 'teacher_user' in models and (teacher or teacher_user):
            models['teacher_user'] = mixer.blend('auth.User')
            self.teacher_user = user

        if not 'teacher_cohort_user' in models and teacher:
            kargs = {
                'user': models['teacher_user'],
                'cohort': models['cohort'],
                'role': 'TEACHER',
            }

            models['teacher_cohort_user'] = mixer.blend(
                'admissions.CohortUser', **kargs)

        return models
