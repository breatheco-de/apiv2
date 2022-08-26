"""
Tasks tests
"""
import re
from unittest.mock import MagicMock, call, patch
from breathecode.utils import APIException
from django.utils import timezone
from ...actions import generate_certificate, strings
import breathecode.certificate.signals as signals
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
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__with_user_without_cohort(self):
        model = self.generate_models(user=True)
        try:
            generate_certificate(model['user'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-cohort-user')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 without CohortUser
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_cohort_user(self):
        model = self.generate_models(user=True, cohort=True)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-cohort-user')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Cohort not ended
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__cohort_not_ended(self):
        cohort_user_kwargs = {
            'finantial_status': 'FULLY_PAID',
            'educational_status': 'GRADUATED',
        }
        cohort_kwargs = {
            'current_day': 43877965,
        }
        syllabus_kwargs = {
            'duration_in_days': 43877965,
        }
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty=True,
                                     syllabus_schedule=True,
                                     layout_design=True,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_kwargs=syllabus_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        translation = strings[model['cohort'].language]
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': (teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name),
            'signed_by_role': translation['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'token': None,
            'status_text': 'cohort-without-status-ended',
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 without SyllabusVersion
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_syllabus_version(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True, cohort=True, cohort_user=True, cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-syllabus-version')

        self.assertEqual(self.all_user_specialty_dict(), [])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 without Specialty
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_specialty(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_schedule=True,
                                     syllabus_version=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-specialty')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 without Syllabus
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_syllabus(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'missing-specialty')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 without default Layout
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_specialty_layout(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'no-default-layout')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 without main teacher
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_teacher(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'without-main-teacher')

        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Bad financial status
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_with_bad_student_financial_status(self):
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        translation = strings[model['cohort'].language]
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': (teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name),
            'signed_by_role': translation['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'token': None,
            'status_text': 'bad-finantial-status',
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Student with pending tasks
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__with_student_that_didnt_finish_tasks(self):
        cohort_kwargs = {'stage': 'ENDED'}
        task_kwargs = {'task_type': 'PROJECT', 'revision_status': 'PENDING'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE'}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            #  syllabus_version=True,
            syllabus_version={
                'id': 1,
                'json': {
                    'days': [{
                        'assignments': [{
                            'slug': 'testing-slug',
                            'mandatory': True
                        }]
                    }]
                }
            },
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            task={'associated_slug': 'testing-slug'},
            task_kwargs=task_kwargs,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'token': None,
            'status_text': 'with-pending-tasks',
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Student not graduated
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__without_proper_educational_status(self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'FULLY_PAID'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'status_text': 'bad-educational-status',
            'token': None,
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Student with bad finantial_status
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__with_cohort_user__with_finantial_status_eq_up_to_date(self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)
        self.assertToken(result['token'])
        result['token'] = None

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'status_text': 'bad-educational-status',
            'token': None,
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Student dropped
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__with_cohort_user__with_educational_status_eq_dropped(self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'DROPPED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)

        self.assertToken(result['token'])
        result['token'] = None

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'status_text': 'bad-educational-status',
            'token': None,
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(self.clear_keys(self.all_user_specialty_dict(), ['preview_url', 'token']),
                         [expected])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Cohort not finished
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__with_cohort_not_finished(self):
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'issued_at': None,
            'status': 'ERROR',
            'status_text': 'cohort-not-finished',
            'user_id': 1,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()), [{
            **expected,
            'token': token,
        }])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Generate certificate
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate(self):
        cohort_kwargs = {'stage': 'ENDED', 'current_day': 9545799}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        syllabus_kwargs = {'duration_in_days': 9545799}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     syllabus_kwargs=syllabus_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)
        end = timezone.now()
        issued_at = result['issued_at']
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del result['issued_at']
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()), [{
            **expected, 'token': token,
            'issued_at': issued_at
        }])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Translations
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__lang_en(self):
        cohort_kwargs = {'stage': 'ENDED', 'current_day': 9545799, 'language': 'en'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        syllabus_kwargs = {'duration_in_days': 9545799}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     syllabus_kwargs=syllabus_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)
        end = timezone.now()
        issued_at = result['issued_at']
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)

        del result['issued_at']

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()), [{
            **expected, 'token': token,
            'issued_at': issued_at
        }])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__lang_es(self):
        cohort_kwargs = {'stage': 'ENDED', 'current_day': 9545799, 'language': 'es'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        syllabus_kwargs = {'duration_in_days': 9545799}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     syllabus_kwargs=syllabus_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)
        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model['user'], model['cohort']).__dict__)
        end = timezone.now()
        issued_at = result['issued_at']
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del result['issued_at']

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        expected = {
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': strings[model['cohort'].language]['Main Instructor'],
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
            'update_hash': self.generate_update_hash(user_specialty),
        }

        self.assertToken(result['token'])
        token = result['token']
        del result['token']

        self.assertEqual(result, expected)
        del expected['is_cleaned']

        self.assertEqual(self.clear_preview_url(self.all_user_specialty_dict()), [{
            **expected, 'token': token,
            'issued_at': issued_at
        }])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])

    """
    🔽🔽🔽 Retry generate certificate
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate__retry_generate_certificate(self):
        cohort_kwargs = {'stage': 'ENDED', 'current_day': 9545799}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        syllabus_kwargs = {'duration_in_days': 9545799}
        user_specialty_kwargs = {'status': 'PERSISTED'}
        model = self.generate_models(user=True,
                                     cohort=True,
                                     cohort_user=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_schedule=True,
                                     specialty=True,
                                     layout_design=True,
                                     user_specialty=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     syllabus_kwargs=syllabus_kwargs,
                                     user_specialty_kwargs=user_specialty_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        self.generate_models(user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base)

        try:
            generate_certificate(model['user'], model['cohort'])
            assert False
        except Exception as e:
            self.assertEqual(str(e), 'already-exists')

        user_specialty = self.model_to_dict(model, 'user_specialty')
        del user_specialty['is_cleaned']

        self.assertEqual(self.all_user_specialty_dict(), [user_specialty])

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=user_specialty, sender=user_specialty.__class__),
        ])
