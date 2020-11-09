"""
Collections of mixins used to login in authorize microservice
"""
from unittest.mock import patch, mock_open, create_autospec, MagicMock
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_successful_models(self):
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

        layout_design = mixer.blend('certificate.LayoutDesign')
        layout_design.slug = 'default'
        layout_design.save()
        self.layout_design = layout_design

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

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate
        cohort.stage = 'ENDED'
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.save()
        self.cohort_user = cohort_user

        teacher_user = mixer.blend('auth.User')
        teacher_user.save()
        self.teacher_user = user

        # teacher_cohort = mixer.blend('admissions.Cohort')
        # # cohort.certificate = certificate
        # teacher_cohort.save()
        # self.teacher_cohort = teacher_cohort

        teacher_cohort_user = mixer.blend('admissions.CohortUser')
        teacher_cohort_user.user = teacher_user
        teacher_cohort_user.cohort = cohort
        teacher_cohort_user.role = 'TEACHER'
        teacher_cohort_user.save()
        self.teacher_cohort_user = teacher_cohort_user

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models_without_specialty(self):
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

        # user as certificate
        user_specialty = mixer.blend('certificate.UserSpecialty')
        user_specialty.token = self.token
        user_specialty.save()
        self.user_specialty = user_specialty

        user = mixer.blend('auth.User')
        user.save()
        self.user = user

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.save()
        self.cohort_user = cohort_user

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models_without_layout(self):
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

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

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.save()
        self.cohort_user = cohort_user

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models_without_master_teacher(self):
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

        layout_design = mixer.blend('certificate.LayoutDesign')
        layout_design.slug = 'default'
        layout_design.save()
        self.layout_design = layout_design

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

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.save()
        self.cohort_user = cohort_user

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def generate_models_with_stage_ended(self):
        certificate = mixer.blend('admissions.Certificate')
        certificate.save()
        self.certificate = certificate

        layout_design = mixer.blend('certificate.LayoutDesign')
        layout_design.slug = 'default'
        layout_design.save()
        self.layout_design = layout_design

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

        cohort = mixer.blend('admissions.Cohort')
        cohort.certificate = certificate
        cohort.save()
        self.cohort = cohort

        cohort_user = mixer.blend('admissions.CohortUser')
        cohort_user.user = user
        cohort_user.cohort = cohort
        cohort_user.save()
        self.cohort_user = cohort_user

        teacher_user = mixer.blend('auth.User')
        teacher_user.save()
        self.teacher_user = user

        teacher_cohort_user = mixer.blend('admissions.CohortUser')
        teacher_cohort_user.user = teacher_user
        teacher_cohort_user.cohort = cohort
        teacher_cohort_user.role = 'TEACHER'
        teacher_cohort_user.save()
        self.teacher_cohort_user = teacher_cohort_user
