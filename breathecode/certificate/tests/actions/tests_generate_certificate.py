"""
Tasks tests
"""
import re
from unittest.mock import patch
from breathecode.utils import APIException
from ...actions import generate_certificate, strings
from ..mixins import CertificateTestCase
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)


class ActionGenerateCertificateTestCase(CertificateTestCase):
    """
    🔽🔽🔽 With User and without Cohort
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__with_user_without_cohort(self):
        model = self.generate_models(user=True)
        try:
            self.assertEqual(generate_certificate(model['user']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-cohort-user')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without CohortUser
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_cohort_user(self):
        model = self.generate_models(user=True, cohort=True)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-cohort-user')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without SyllabusVersion
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_syllabus_version(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-syllabus-version')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without SpecialtyMode
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_certificate(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-specialty-mode')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without Specialty
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_specialty(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     specialty_mode=True,
                                     syllabus_version=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-specialty')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without Syllabus
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_syllabus(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-specialty')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without default Layout
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_specialty_layout(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'no-default-layout')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 without main teacher
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_teacher(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            self.assertEqual(
                generate_certificate(model['user'], model['cohort']), None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'without-main-teacher')

        self.assertEqual(self.all_user_specialty_dict(), [])

    """
    🔽🔽🔽 Bad financial status
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_bad_student_financial_status(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(
            user=True,
            cohort_user=True,
            cohort_user_kwargs=cohort_user_kwargs,
            models=base)
        result = self.remove_dinamics_fields(
            generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        translation = strings[model['cohort'].language]
        expected = {
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            None,
            'signed_by': (teacher_model['user'].first_name + " " +
                          teacher_model['user'].last_name),
            'signed_by_role':
            translation["Main Instructor"],
            'specialty_id':
            1,
            'status':
            'ERROR',
            'token':
            None,
            'status_text': ('The student must have finantial status '
                            'FULLY_PAID or UP_TO_DATE'),
            'user_id':
            1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.all_user_specialty_dict(),
                            ["preview_url", "token"]), [expected])

    """
    🔽🔽🔽 Student with pending tasks
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__with_student_that_didnt_finish_tasks(self):
        cohort_kwargs = {'stage': 'ENDED'}
        task_kwargs = {'type': 'PROJECT'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     task=True,
                                     task_kwargs=task_kwargs,
                                     cohort_kwargs=cohort_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(
            user=True,
            cohort_user=True,
            cohort_user_kwargs=cohort_user_kwargs,
            models=base)
        result = self.remove_dinamics_fields(
            generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        expected = {
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            None,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            strings[model['cohort'].language]["Main Instructor"],
            'specialty_id':
            1,
            'status':
            'ERROR',
            'token':
            None,
            'status_text':
            'The student has 1 pending tasks',
            'user_id':
            1,
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.all_user_specialty_dict(),
                            ["preview_url", "token"]), [expected])

    """
    🔽🔽🔽 Student not graduated
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__without_proper_educational_status(self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'FULLY_PAID'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(
            user=True,
            cohort_user=True,
            cohort_user_kwargs=cohort_user_kwargs,
            models=base)
        result = self.remove_dinamics_fields(
            generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        expected = {
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            None,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            strings[model['cohort'].language]["Main Instructor"],
            'specialty_id':
            1,
            'status':
            'ERROR',
            'status_text':
            'The student must have educational status GRADUATED',
            'token':
            None,
            'user_id':
            1,
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.all_user_specialty_dict(),
                            ["preview_url", "token"]), [expected])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__with_cohort_user__with_finantial_status_eq_up_to_date(
            self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(
            user=True,
            cohort_user=True,
            cohort_user_kwargs=cohort_user_kwargs,
            models=base)
        result = self.remove_dinamics_fields(
            generate_certificate(model['user'], model['cohort']).__dict__)
        self.assertToken(result["token"])
        result["token"] = None

        expected = {
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            None,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            strings[model['cohort'].language]["Main Instructor"],
            'specialty_id':
            1,
            'status':
            'ERROR',
            'status_text':
            'The student must have educational status GRADUATED',
            'token':
            None,
            'user_id':
            1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.all_user_specialty_dict(),
                            ["preview_url", "token"]), [expected])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate__with_cohort_user__with_educational_status_eq_dropped(
            self):
        """
        Step 11
        Tests generate_certificate with CohortUser educational_status eq
        DROPPED
        Status: BAD_REQUEST
        """
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {
            'finantial_status': 'UP_TO_DATE',
            'educational_status': 'DROPPED'
        }
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(
            user=True,
            cohort_user=True,
            cohort_user_kwargs=cohort_user_kwargs,
            models=base)
        result = self.remove_dinamics_fields(
            generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        expected = {
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            None,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            strings[model['cohort'].language]["Main Instructor"],
            'specialty_id':
            1,
            'status':
            'ERROR',
            'status_text':
            'The student must have educational status GRADUATED',
            'token':
            None,
            'user_id':
            1,
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.all_user_specialty_dict(),
                            ["preview_url", "token"]), [expected])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_generate_certificate_with_cohort_user_not_finished(self):
    #     """
    #     Step 12
    #     Tests generate_certificate with CohortUser educational_status eq
    #     GRADUATED
    #     Status: BAD_REQUEST
    #     """
    #     model = self.generate_models(
    #         user=True,
    #         cohort=True,
    #         cohort_user=True,
    #         specialty=True,
    #         layout_design=True,
    #         cohort_finished=True,
    #         cohort_user_finantial_status='UP_TO_DATE',
    #         syllabus=True,
    #         cohort_user_educational_status='GRADUATED')

    #     base = model.copy()
    #     del base['user']
    #     del base['cohort_user']

    #     teacher_model = self.generate_models(user=True,
    #                                          cohort_user=True,
    #                                          cohort_user_role='TEACHER',
    #                                          models=base)
    #     result = self.remove_dinamics_fields(
    #         generate_certificate(model['user'], model['cohort']).__dict__)
    #     expected = {
    #         'academy_id':
    #         1,
    #         'cohort_id':
    #         1,
    #         'expires_at':
    #         None,
    #         'id':
    #         1,
    #         'layout_id':
    #         1,
    #         'preview_url':
    #         None,
    #         'signed_by':
    #         teacher_model['user'].first_name + " " +
    #         teacher_model['user'].last_name,
    #         'signed_by_role':
    #         strings[model['cohort'].language]["Main Instructor"],
    #         'specialty_id':
    #         1,
    #         'status':
    #         'ERROR',
    #         'status_text':
    #         "The student cohort stage has to be 'ENDED' "
    #         'before you can issue any certificates',
    #         'user_id':
    #         1,
    #     }

    #     self.assertToken(result['token'])
    #     token = result['token']
    #     del result['token']

    #     self.assertEqual(result, expected)

    #     self.assertEqual(
    #         self.clear_preview_url(self.all_user_specialty_dict()),
    #         [{
    #             **expected, 'token': token
    #         }])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_generate_certificate(self):
    #     """
    #     Step 13
    #     Tests generate_certificate with Cohort stage eq ENDED
    #     Status: OK
    #     """
    #     model = self.generate_models(
    #         user=True,
    #         cohort=True,
    #         cohort_user=True,
    #         specialty=True,
    #         layout_design=True,
    #         cohort_finished=True,
    #         cohort_user_finantial_status='UP_TO_DATE',
    #         syllabus=True,
    #         cohort_user_educational_status='GRADUATED',
    #         cohort_stage='ENDED')

    #     base = model.copy()
    #     del base['user']
    #     del base['cohort_user']

    #     teacher_model = self.generate_models(user=True,
    #                                          cohort_user=True,
    #                                          cohort_user_role='TEACHER',
    #                                          models=base)
    #     result = self.remove_dinamics_fields(
    #         generate_certificate(model['user'], model['cohort']).__dict__)
    #     expected = {
    #         'academy_id':
    #         1,
    #         'cohort_id':
    #         1,
    #         'expires_at':
    #         None,
    #         'id':
    #         1,
    #         'layout_id':
    #         1,
    #         'preview_url':
    #         None,
    #         'signed_by':
    #         teacher_model['user'].first_name + " " +
    #         teacher_model['user'].last_name,
    #         'signed_by_role':
    #         strings[model['cohort'].language]["Main Instructor"],
    #         'specialty_id':
    #         1,
    #         'status':
    #         'PERSISTED',
    #         'status_text':
    #         'Certificate successfully queued for PDF generation',
    #         'user_id':
    #         1,
    #         'is_cleaned':
    #         True,
    #     }

    #     self.assertToken(result['token'])
    #     token = result['token']
    #     del result['token']

    #     self.assertEqual(result, expected)
    #     del expected['is_cleaned']

    #     self.assertEqual(
    #         self.clear_preview_url(self.all_user_specialty_dict()),
    #         [{
    #             **expected, 'token': token
    #         }])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_generate_certificate_lang_en(self):
    #     """
    #     Step 14
    #     Tests generate_certificate with language in english
    #     Status: OK
    #     """
    #     model = self.generate_models(
    #         user=True,
    #         cohort=True,
    #         cohort_user=True,
    #         specialty=True,
    #         layout_design=True,
    #         cohort_finished=True,
    #         cohort_user_finantial_status='UP_TO_DATE',
    #         syllabus=True,
    #         cohort_user_educational_status='GRADUATED',
    #         cohort_stage='ENDED',
    #         language='en')

    #     base = model.copy()
    #     del base['user']
    #     del base['cohort_user']

    #     teacher_model = self.generate_models(user=True,
    #                                          cohort_user=True,
    #                                          cohort_user_role='TEACHER',
    #                                          models=base)
    #     result = self.remove_dinamics_fields(
    #         generate_certificate(model['user'], model['cohort']).__dict__)
    #     expected = {
    #         'academy_id':
    #         1,
    #         'cohort_id':
    #         1,
    #         'expires_at':
    #         None,
    #         'id':
    #         1,
    #         'layout_id':
    #         1,
    #         'preview_url':
    #         None,
    #         'signed_by':
    #         teacher_model['user'].first_name + " " +
    #         teacher_model['user'].last_name,
    #         'signed_by_role':
    #         strings[model['cohort'].language]["Main Instructor"],
    #         'specialty_id':
    #         1,
    #         'status':
    #         'PERSISTED',
    #         'status_text':
    #         'Certificate successfully queued for PDF generation',
    #         'user_id':
    #         1,
    #         'is_cleaned':
    #         True,
    #     }

    #     self.assertToken(result['token'])
    #     token = result['token']
    #     del result['token']

    #     self.assertEqual(result, expected)
    #     del expected['is_cleaned']

    #     self.assertEqual(
    #         self.clear_preview_url(self.all_user_specialty_dict()),
    #         [{
    #             **expected, 'token': token
    #         }])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_generate_certificate_lang_es(self):
    #     """
    #     Step 15
    #     Tests generate_certificate with language in spanish
    #     Status: OK
    #     """
    #     model = self.generate_models(
    #         user=True,
    #         cohort=True,
    #         cohort_user=True,
    #         specialty=True,
    #         layout_design=True,
    #         cohort_finished=True,
    #         cohort_user_finantial_status='UP_TO_DATE',
    #         syllabus=True,
    #         cohort_user_educational_status='GRADUATED',
    #         cohort_stage='ENDED',
    #         language='es')

    #     base = model.copy()
    #     del base['user']
    #     del base['cohort_user']

    #     teacher_model = self.generate_models(user=True,
    #                                          cohort_user=True,
    #                                          cohort_user_role='TEACHER',
    #                                          models=base)
    #     result = self.remove_dinamics_fields(
    #         generate_certificate(model['user'], model['cohort']).__dict__)
    #     expected = {
    #         'academy_id':
    #         1,
    #         'cohort_id':
    #         1,
    #         'expires_at':
    #         None,
    #         'id':
    #         1,
    #         'layout_id':
    #         1,
    #         'preview_url':
    #         None,
    #         'signed_by':
    #         teacher_model['user'].first_name + " " +
    #         teacher_model['user'].last_name,
    #         'signed_by_role':
    #         strings[model['cohort'].language]["Main Instructor"],
    #         'specialty_id':
    #         1,
    #         'status':
    #         'PERSISTED',
    #         'status_text':
    #         'Certificate successfully queued for PDF generation',
    #         'user_id':
    #         1,
    #         'is_cleaned':
    #         True,
    #     }

    #     self.assertToken(result['token'])
    #     token = result['token']
    #     del result['token']

    #     self.assertEqual(result, expected)
    #     del expected['is_cleaned']

    #     self.assertEqual(
    #         self.clear_preview_url(self.all_user_specialty_dict()),
    #         [{
    #             **expected, 'token': token
    #         }])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_generate_certificate_repeated_certificate(self):
    #     """
    #     Step 16
    #     Tests dennyy generate_certificate that is already created for same student
    #     in same cohort
    #     Status: BAD_REQUEST
    #     """
    #     model = self.generate_models(
    #         user=True,
    #         cohort=True,
    #         cohort_user=True,
    #         specialty=True,
    #         layout_design=True,
    #         cohort_finished=True,
    #         cohort_user_finantial_status='UP_TO_DATE',
    #         syllabus=True,
    #         cohort_user_educational_status='GRADUATED',
    #         cohort_stage='ENDED')

    #     base = model.copy()
    #     del base['user']
    #     del base['cohort_user']

    #     teacher_model = self.generate_models(user=True,
    #                                          cohort_user=True,
    #                                          cohort_user_role='TEACHER',
    #                                          models=base)
    #     result = generate_certificate(model['user'], model['cohort'])

    #     result.preview_url = 'http://potato.io'
    #     result.save()
    #     result = self.remove_dinamics_fields(result.__dict__)

    #     try:
    #         generate_certificate(model['user'], model['cohort'])
    #         assert False
    #     except APIException as e:
    #         self.assertEqual(str(e),
    #                          "This user already has a certificate created")

    #     expected = {
    #         'academy_id':
    #         1,
    #         'cohort_id':
    #         1,
    #         'expires_at':
    #         None,
    #         'id':
    #         1,
    #         'layout_id':
    #         1,
    #         'preview_url':
    #         None,
    #         'signed_by':
    #         teacher_model['user'].first_name + " " +
    #         teacher_model['user'].last_name,
    #         'signed_by_role':
    #         strings[model['cohort'].language]["Main Instructor"],
    #         'specialty_id':
    #         1,
    #         'status':
    #         'PERSISTED',
    #         'status_text':
    #         'Certificate successfully queued for PDF generation',
    #         'user_id':
    #         1,
    #         'is_cleaned':
    #         True,
    #         'preview_url':
    #         'http://potato.io',
    #     }

    #     self.assertToken(result['token'])
    #     token = result['token']
    #     del result['token']

    #     self.assertEqual(result, expected)
    #     del expected['is_cleaned']
    #     self.assertEqual(self.all_user_specialty_dict(),
    #                      [{
    #                          **expected, 'token': token
    #                      }])
