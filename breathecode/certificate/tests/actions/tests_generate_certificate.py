"""
Tasks tests
"""
from breathecode.certificate.models import PERSISTED
import re
from unittest.mock import patch
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Certificate
from breathecode.utils import ValidationException, APIException
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
    def test_generate_certificate_with_user_without_cohort(self):
        """
        Step 1
        Tests generate_certificate with a User that has no cohort
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True)
        try:
            self.assertEqual(generate_certificate(model['user']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'Impossible to obtain the student cohort,'
                ' maybe it\'s none assigned')

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_cohort_user(self):
        """
        Step 2
        Tests generate_certificate with Cohort but without CohortUser
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

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_syllabus(self):
        """
        Step 3
        Tests generate_certificate with CohortUser
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True, cohort_stage='ENDED')
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            cohort_name = model['cohort'].name
            self.assertEqual(str(e), 'The cohort has no syllabus assigned, '
                f'please set a syllabus for cohort: {cohort_name}')

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_certificate(self):
        """
        Step 4
        Tests generate_certificate with Syllabus but Without Certificate
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            syllabus=True, cohort_stage='ENDED')
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            certificate_name = model['syllabus'].certificate.name
            self.assertEqual(str(e), 'Specialty has no certificate assigned, '
                'please set a certificate on the Specialty model: '
                f'{certificate_name}')

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_specialty_layout(self):
        """
        Step 5
        Tests generate_certificate with Specialty btu missing a default layout
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, syllabus=True, cohort_stage='ENDED')
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'Missing a default layout')

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_teacher(self):
        """
        Step 6
        Tests generate_certificate without Teacher
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, syllabus=True, cohort_stage='ENDED')
        try:
            self.assertEqual(generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'This cohort does not have a main '
                'teacher, please assign it first')

        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_bad_student_financial_status(self):
        """
        Step 7
        Tests generate_certificate with bad student financial status
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, syllabus=True, cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

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
            'token': None,
            'status_text': 'The student must have finantial status FULLY_PAID '
                'or UP_TO_DATE',
            'user_id': 1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ["preview_url", "token"]),[expected])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_student_that_didnt_finish_tasks(self):
        """
        Step 8
        Tests generate_certificate with students that are missing to deliver all the tasks
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, task=True, task_type='PROJECT',
            syllabus=True, cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

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
            'token': None,
            'status_text': 'The student has 1 pending tasks',
            'user_id': 1,
        }
        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ["preview_url", "token"]),[expected])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_proper_educational_status(self):
        """
        Step 9
        Tests generate_certificate without CohortUser educational status GRADUATED
        Status: BAD_REQUEST
        """
        model = self.generate_models(user=True, cohort=True, cohort_user=True,
            specialty=True, layout_design=True, cohort_user_finantial_status='FULLY_PAID',
            syllabus=True, cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

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
            'token': None,
            'user_id': 1,
        }
        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ["preview_url", "token"]),[expected])

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
            syllabus=True, cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)
        self.assertToken(result["token"])
        result["token"] = None
        
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
            'token': None,
            'user_id': 1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ["preview_url", "token"]),[expected])

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
            cohort_user_educational_status='DROPPED', cohort_stage='ENDED')

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True,
        cohort_user_role='TEACHER', models=base)
        result = self.remove_dinamics_fields(generate_certificate(
            model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

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
            'token': None,
            'user_id': 1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ["preview_url", "token"]),[expected])

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
            'status_text': "The student cohort stage has to be 'ENDED' "
                'before you can issue any certificates',
            'user_id': 1,
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])

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

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])

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

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])

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

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()),
            [{**expected, 'token': token}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_repeated_certificate(self):
        """
        Step 16
        Tests dennyy generate_certificate that is already created for same student
        in same cohort
        Status: BAD_REQUEST
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
        result = generate_certificate(model['user'], model['cohort'])
        
        result.preview_url = 'http://potato.io'
        result.save()
        result = self.remove_dinamics_fields(result.__dict__)
        
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False        
        except APIException as e:
            self.assertEqual(str(e), "This user already has a certificate created")
        
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
            'preview_url': 'http://potato.io',
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']
        self.assertEqual(self.all_user_specialty_dict(), [{**expected, 'token': token}])
        