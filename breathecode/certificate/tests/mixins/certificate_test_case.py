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
    user = None
    cohort = None
    cohort_user = None
    certificate = None
    specialty = None
    user_specialty = None
    layout_design = None
    teacher_user = None
    teacher_cohort = None
    teacher_cohort_user = None
    task = None

    def user_specialty_has_preview_url(self, certificate_id):
        """preview_url is set?"""
        certificate = UserSpecialty.objects.get(id=certificate_id)
        return certificate.preview_url is not None

    def generate_screenshotmachine_url(self):
        """Generate screenshotmachine url"""
        certificate = self.user_specialty
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
    def generate_models(self, language: str=None, stage=False, teacher=False, layout=False,
                        specialty=False, finished=False, finantial_status=None, task=None):
        """Generate models"""
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

        if layout:
            layout_design = mixer.blend('certificate.LayoutDesign')
            layout_design.slug = 'default'
            layout_design.save()
            self.layout_design = layout_design

        if specialty:
            specialty = mixer.blend('certificate.Specialty')
            specialty.certificate = certificate
            specialty.save()
            self.specialty = specialty

        # user as certificate
        user_specialty = mixer.blend('certificate.UserSpecialty')
        user_specialty.token = self.token
        user_specialty.save()
        self.user_specialty = user_specialty

        user = mixer.blend('auth.User')
        user.save()
        self.user = user

        if task:
            task = mixer.blend('assignments.Task')
            task.user = user
            task.revision_status = PENDING
            task.task_type = PROJECT
            task.save()
            self.task = task

        cohort = mixer.blend('admissions.Cohort')

        if finished:
            cohort.current_day = certificate.duration_in_days

        cohort.certificate = certificate

        if stage:
            cohort.stage = 'ENDED'

        if language:
            cohort.language = language

        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.educational_status = 'GRADUATED'

        if finantial_status:
            cohort_user.finantial_status = finantial_status

        cohort_user.save()
        self.cohort_user = cohort_user

        if teacher:
            teacher_user = mixer.blend('auth.User')
            teacher_user.save()
            self.teacher_user = user

            teacher_cohort_user = mixer.blend('admissions.CohortUser')
            teacher_cohort_user.user = teacher_user
            teacher_cohort_user.cohort = cohort
            teacher_cohort_user.role = 'TEACHER'
            teacher_cohort_user.save()
            self.teacher_cohort_user = teacher_cohort_user
