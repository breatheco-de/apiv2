"""
Tasks tests
"""
from breathecode.certificate.models import PERSISTED
import re
from unittest.mock import patch
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Certificate
from breathecode.utils import ValidationException
from ...actions import generate_certificate, strings
from ..mixins.new_certificate_test_case import CertificateTestCase
from ....admissions.models import FULLY_PAID, UP_TO_DATE, LATE
# from .mocks import CertificateBreathecodeMock
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    # GOOGLE_CLOUD_INSTANCES
)


class ActionGenerateCertificateTestCase(CertificateTestCase):
    """Tests action generate_certificate"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_user(self):
        """
        Step 1
        Tests generate_certificate with User
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True)
        try:
            self.assertEqual(generate_certificate(model['user']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'Impossible to obtain the student cohort,'
                ' maybe it\'s none assigned')

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [])
        self.assertEqual(self.all_specialty_dict(), [])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [])
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort(self):
        """
        Step 2
        Tests generate_certificate with Cohort
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True)
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            print(e)
            self.assertEqual(str(e), 'Impossible to obtain the student cohort,'
                ' maybe it\'s none assigned')

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [])
        self.assertEqual(self.all_specialty_dict(), [])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort_user(self):
        """
        Step 3
        Tests generate_certificate with CohortUser
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True)
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            cohort_name = model['cohort'].name
            self.assertEqual(str(e), 'The cohort has no syllabus assigned, '
                f'please set a syllabus for cohort: {cohort_name}')

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [])
        self.assertEqual(self.all_specialty_dict(), [])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        }])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_syllabus(self):
        """
        Step 4
        Tests generate_certificate with Syllabus
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            syllabus=True)
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            certificate_name = model['syllabus'].certificate.name
            self.assertEqual(str(e), 'Specialty has no certificate assigned, '
                'please set a certificate on the Specialty model: '
                f'{certificate_name}')

        self.assertEqual(self.all_syllabus_dict(), [{
            'academy_owner_id': model['syllabus'].academy_owner_id,
            'certificate_id': model['syllabus'].certificate_id,
            'github_url': model['syllabus'].github_url,
            'id': model['syllabus'].id,
            'json': model['syllabus'].json,
            'private': model['syllabus'].private,
            'version': model['syllabus'].version
        }])
        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [])
        self.assertEqual(self.all_specialty_dict(), [])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        }])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_specialty(self):
        """
        Step 5
        Tests generate_certificate with Specialty
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, syllabus=True)
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'Missing a default layout')

        self.assertEqual(self.all_syllabus_dict(), [{
            'academy_owner_id': model['syllabus'].academy_owner_id,
            'certificate_id': model['syllabus'].certificate_id,
            'github_url': model['syllabus'].github_url,
            'id': model['syllabus'].id,
            'json': model['syllabus'].json,
            'private': model['syllabus'].private,
            'version': model['syllabus'].version
        }])
        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        }])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_layout_design(self):
        """
        Step 6
        Tests generate_certificate with LayoutDesign
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, syllabus=True)
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'This cohort does not have a main '
                'teacher, please assign it first')

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.all_user_specialty_dict(), [])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        }])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_user_with_role_teacher(self):
        """
        Step 7
        Tests generate_certificate with User with role teacher
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, syllabus=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': 'The student must have finantial status FULLY_PAID '
                'or UP_TO_DATE',
            'token': '',
            'user_id': 1,
        }
        self.assertEqual(result, expected)

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [expected])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_task(self):
        """
        Step 8
        Tests generate_certificate with Task type PROJECT
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, task=True, task_type='PROJECT',
            syllabus=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': 'The student has 1 pending tasks',
            'token': '',
            'user_id': 1,
        }
        self.assertEqual(result, expected)

        self.assertEqual(self.all_task_dict(), [{
            'associated_slug': model['task'].associated_slug,
            'cohort_id': model['task'].cohort_id,
            'description': model['task'].description,
            'github_url': model['task'].github_url,
            'id': model['task'].id,
            'live_url': model['task'].live_url,
            'revision_status': 'PENDING',
            'task_status': 'PENDING',
            'task_type': 'PROJECT',
            'title': model['task'].title,
            'user_id': model['task'].user_id
        }])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [expected])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort_user_with_finantial_status_eq_fully_paid(self):
        """
        Step 9
        Tests generate_certificate with CohortUser eq FULLY_PAID
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_user_finantial_status='FULLY_PAID',
            syllabus=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': 'The student must have educational status GRADUATED',
            'token': '',
            'user_id': 1,
        }
        self.assertEqual(result, expected)

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [expected])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort_user_with_finantial_status_eq_up_to_date(self):
        """
        Step 10
        Tests generate_certificate with CohortUser eq UP_TO_DATE
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_user_finantial_status='UP_TO_DATE',
            syllabus=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': 'The student must have educational status GRADUATED',
            'token': '',
            'user_id': 1,
        }
        self.assertEqual(result, expected)

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [expected])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort_user_with_educational_status_eq_dropped(self):
        """
        Step 11
        Tests generate_certificate with CohortUser educational_status eq
        DROPPED
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, syllabus=True,
            cohort_user_finantial_status='UP_TO_DATE',
            cohort_user_educational_status='DROPPED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': 'The student must have educational status GRADUATED',
            'token': '',
            'user_id': 1,
        }
        self.assertEqual(result, expected)

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [expected])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_cohort_user_not_finished(self):
        """
        Step 12
        Tests generate_certificate with CohortUser educational_status eq
        GRADUATED
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_finished=True,
            cohort_user_finantial_status='UP_TO_DATE', syllabus=True,
            cohort_user_educational_status='GRADUATED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' "
                'before you can issue any certificates',
            'user_id': 1,
            'is_cleaned': True,
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate(self):
        """
        Step 13
        Tests generate_certificate with Cohort stage eq ENDED
        Status: OK
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_finished=True,
            cohort_user_finantial_status='UP_TO_DATE', syllabus=True,
            cohort_user_educational_status='GRADUATED',
            cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_en(self):
        """
        Step 14
        Tests generate_certificate with language in english
        Status: OK
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_finished=True,
            cohort_user_finantial_status='UP_TO_DATE', syllabus=True,
            cohort_user_educational_status='GRADUATED',
            cohort_stage='ENDED', language='en')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_es(self):
        """
        Step 15
        Tests generate_certificate with language in spanish
        Status: OK
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_finished=True,
            cohort_user_finantial_status='UP_TO_DATE', syllabus=True,
            cohort_user_educational_status='GRADUATED',
            cohort_stage='ENDED', language='es')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.all_task_dict(), [])
        self.assertEqual(self.all_layout_design_dict(), [{
            'id': model['layout_design'].id,
            'name': model['layout_design'].name,
            'slug': 'default'
        }])
        self.assertEqual(self.all_specialty_dict(), [{
            'certificate_id': model['specialty'].certificate_id,
            'description': model['specialty'].description,
            'duration_in_hours': model['specialty'].duration_in_hours,
            'expiration_day_delta': model['specialty'].expiration_day_delta,
            'id': model['specialty'].id,
            'logo_url': model['specialty'].logo_url,
            'name': model['specialty'].name,
            'slug': model['specialty'].slug,
        }])
        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': model['cohort_user'].cohort_id,
            'educational_status': model['cohort_user'].educational_status,
            'finantial_status': model['cohort_user'].finantial_status,
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'user_id': model['cohort_user'].user_id,
        } for model in [model, teacher_model]])
        self.assertEqual(self.all_cohort_dict(), [{
            'academy_id': model['cohort'].academy_id,
            'syllabus_id': model['cohort'].syllabus_id,
            'current_day': model['cohort'].current_day,
            'ending_date': model['cohort'].ending_date,
            'id': model['cohort'].id,
            'kickoff_date': model['cohort'].kickoff_date,
            'language': model['cohort'].language,
            'name': model['cohort'].name,
            'slug': model['cohort'].slug,
            'stage': model['cohort'].stage,
            'timezone': model['cohort'].timezone
        }])
        self.assertEqual(self.all_user_dict(), [{
            'date_joined': model['user'].date_joined,
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'id': model['user'].id,
            'is_active': model['user'].is_active,
            'is_staff': model['user'].is_staff,
            'is_superuser': model['user'].is_superuser,
            'last_login': model['user'].last_login,
            'last_name': model['user'].last_name,
            'password': model['user'].password,
            'username': model['user'].username,
        } for model in [model, teacher_model]])
