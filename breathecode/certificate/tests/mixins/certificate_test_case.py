"""
Collections of mixins used to login in authorize microservice
"""
import os
from unittest.mock import patch
from urllib.parse import urlencode
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.assignments.models import PENDING, PROJECT
from breathecode.certificate.models import UserSpecialty
from .development_environment import DevelopmentEnvironment
from ...models import Certificate, Cohort
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock
)

# class CertificateTestCase(TransactionTestCase, DevelopmentEnvironment):
class CertificateTestCase(APITestCase, DevelopmentEnvironment):
    """APITestCase with Certificate models"""
    token = '9e76a2ab3bd55454c384e0a5cdb5298d17285949'

    def remove_model_state(self, dict):
        result = None
        if dict:
            result = dict.copy()
            del result['_state']
        return result

    def remove_updated_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'updated_at' in result:
                del result['updated_at']
        return result

    def remove_dinamics_fields(self, dict):
        return self.remove_updated_at(self.remove_model_state(dict))

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
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Cohort.objects.filter()]

    def all_certificate_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Certificate.objects.filter()]

    def all_user_specialty_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            UserSpecialty.objects.filter()]

    def user_specialty_has_preview_url(self, certificate_id):
        """preview_url is set?"""
        certificate = UserSpecialty.objects.get(id=certificate_id)
        return certificate.preview_url is not None

    def generate_screenshotmachine_url(self, user_specialty):
        """Generate screenshotmachine url"""
        certificate = user_specialty
        query_string = urlencode({
            'key': os.environ.get('SCREENSHOT_MACHINE_KEY'),
            'url': f'https://certificate.breatheco.de/preview/{certificate.token}',
            'device': 'desktop',
            'cacheLimit': '0',
            'dimension': '1024x707',
        })
        return f'https://api.screenshotmachine.com?{query_string}'

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models(self, language='', stage=False, teacher=False, layout_design=False,
            specialty=False, finished=False, finantial_status=None, task=None, cohort=False,
            certificate=False, teacher_user=False, user_specialty=False, user=False,
            cohort_user=False):
        """Generate models"""
        models = {}

        if certificate or specialty or cohort or cohort_user or teacher:
            models['certificate'] = mixer.blend('admissions.Certificate')

        if layout_design:
            models['layout_design'] = mixer.blend('certificate.LayoutDesign', slug='default')

        if specialty:
            kargs = {}

            if certificate:
                kargs['certificate'] = models['certificate']
            
            models['specialty'] = mixer.blend('certificate.Specialty', **kargs)

        if user_specialty:
            models['user_specialty'] = mixer.blend('certificate.UserSpecialty', token=self.token)

        if user or cohort_user or task:
            models['user'] = mixer.blend('auth.User')

        if task:
            kargs = {
                'user': models['user'],
                'revision_status': PENDING,
                'task_type': PROJECT,
            }

            models['task'] = mixer.blend('assignments.Task', **kargs)

        if cohort or cohort_user or teacher:
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

        if cohort_user:
            kargs = {
                'educational_status': 'GRADUATED',
                'user': models['user'],
                'cohort': models['cohort'],
            }

            if finantial_status:
                kargs['finantial_status'] = finantial_status

            models['cohort_user'] = mixer.blend('admissions.CohortUser', **kargs)

        if teacher or teacher_user:
            models['teacher_user'] = mixer.blend('auth.User')
            self.teacher_user = user

        if teacher:
            kargs = {
                'user': models['teacher_user'],
                'cohort': models['cohort'],
                'role': 'TEACHER',
            }

            print(kargs)

            models['teacher_cohort_user'] = mixer.blend('admissions.CohortUser', **kargs)
        
        return models
