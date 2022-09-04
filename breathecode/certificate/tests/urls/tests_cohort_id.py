"""
Test /certificate
"""
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import CertificateTestCase
import breathecode.certificate.signals as signals


class CertificateTestSuite(CertificateTestCase):
    """Test /certificate/cohort/id"""
    """
    🔽🔽🔽 Auth
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_certificate_cohort_user__without_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_certificate_cohort_user__with_auth_without_permissions(self):
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        expected = {
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Post method
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_with_role_student_without_syllabus_version(self):
        """ No main teacher in cohort """
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             syllabus_schedule=True,
                             specialty=True,
                             layout_design=True,
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'cohort-has-no-syllabus-version-assigned', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_with_role_student_without_main_teacher(self):
        """ No main teacher in cohort """
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             syllabus_version=True,
                             syllabus_schedule=True,
                             specialty=True,
                             layout_design=True,
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'without-main-teacher', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_without_cohort_user(self):
        """ No cohort user"""
        self.headers(academy=1)
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_stage='ENDED')

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'no-user-with-student-role', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_with_everything_but_schedule(self):
        """ Should be ok because cohorts dont need specialy mode to generate certificates """
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(
            authenticate=True,
            cohort=True,
            user=True,
            profile_academy=True,
            capability='crud_certificate',
            role='STUDENT',
            syllabus_version=True,
            specialty=True,
            cohort_user=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
        )

        base = model.copy()
        del base['user']
        del base['cohort_user']
        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send.call_args_list,
            [
                # Action
                call(instance=user_specialty, sender=user_specialty.__class__),
            ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_with_role_student_with_syllabus_without_specialty(self):
        """ No specialty """
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             syllabus_version=True,
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'missing-specialty', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_test_without_layout(self):
        """ No specialty """
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             syllabus_version=True,
                             specialty=True,
                             syllabus_schedule=True,
                             cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'no-default-layout', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_test_with_cohort_stage_no_ended(self):
        """ No specialty """
        self.headers(academy=1)
        self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             specialty=True,
                             layout_design=True)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {'detail': 'cohort-stage-must-be-ended', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_test_without_cohort_user_finantial_status(self):
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True,
                                     capability='crud_certificate',
                                     role='STUDENT',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty=True,
                                     syllabus_schedule=True,
                                     user_specialty=True,
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

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(model.cohort.kickoff_date),
                'ending_date': None,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'schedule': {
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                },
                'syllabus_version': {
                    'version': model['syllabus_version'].version,
                    'name': model['syllabus_version'].syllabus.name,
                    'slug': model['syllabus_version'].syllabus.slug,
                    'syllabus': model['syllabus_version'].syllabus.id,
                    'duration_in_days': model['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': model['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': model['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'background_url': model['layout_design'].background_url,
                'slug': model['layout_design'].slug
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'description': model['specialty'].description,
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'issued_at': None,
            'status_text': 'bad-finantial-status',
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            },
            'profile_academy': {
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'status': model['profile_academy'].status,
                'phone': model['profile_academy'].phone,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'academy': {
                    'id': 1,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [{
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': model['user_specialty'].preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'ERROR',
                'issued_at': None,
                'status_text': 'bad-finantial-status',
                'user_id': 1,
                'update_hash': self.generate_update_hash(user_specialty),
                'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949',
            }])

        self.assertEqual(
            signals.user_specialty_saved.send.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Action
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_test_without_cohort_user_educational_status(self):
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True,
                                     capability='crud_certificate',
                                     role='STUDENT',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty=True,
                                     syllabus_schedule=True,
                                     user_specialty=True,
                                     layout_design=True,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     cohort_kwargs=cohort_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(model.cohort.kickoff_date),
                'ending_date': None,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'schedule': {
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                },
                'syllabus_version': {
                    'version': model['syllabus_version'].version,
                    'name': model['syllabus_version'].syllabus.name,
                    'slug': model['syllabus_version'].syllabus.slug,
                    'syllabus': model['syllabus_version'].syllabus.id,
                    'duration_in_days': model['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': model['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': model['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'background_url': model['layout_design'].background_url,
                'slug': model['layout_design'].slug
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'description': model['specialty'].description,
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'issued_at': None,
            'status_text': 'bad-educational-status',
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            },
            'profile_academy': {
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'status': model['profile_academy'].status,
                'phone': model['profile_academy'].phone,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'academy': {
                    'id': 1,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [{
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': model['user_specialty'].preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'ERROR',
                'issued_at': None,
                'status_text': 'bad-educational-status',
                'user_id': 1,
                'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949',
                'update_hash': user_specialty.update_hash,
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_test_with_final_cohort(self):
        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED'}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     capability='crud_certificate',
                                     role='STUDENT',
                                     specialty=True,
                                     syllabus_schedule=True,
                                     user_specialty=True,
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

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(model.cohort.kickoff_date),
                'ending_date': None,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'schedule': {
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                },
                'syllabus_version': {
                    'version': model['syllabus_version'].version,
                    'name': model['syllabus_version'].syllabus.name,
                    'slug': model['syllabus_version'].syllabus.slug,
                    'syllabus': model['syllabus_version'].syllabus.id,
                    'duration_in_days': model['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': model['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': model['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'background_url': model['layout_design'].background_url,
                'slug': model['layout_design'].slug
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'description': model['specialty'].description,
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'issued_at': None,
            'status_text': 'cohort-not-finished',
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            },
            'profile_academy': {
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'status': model['profile_academy'].status,
                'phone': model['profile_academy'].phone,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'academy': {
                    'id': 1,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [{
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': model['user_specialty'].preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'ERROR',
                'issued_at': None,
                'status_text': 'cohort-not-finished',
                'user_id': 1,
                'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949',
                'update_hash': user_specialty.update_hash,
            }])

        self.assertEqual(
            signals.user_specialty_saved.send.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Action
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_generate_certificate_good_request(self):
        """Test /certificate/cohort/id status: 201"""

        self.headers(academy=1)
        cohort_kwargs = {'stage': 'ENDED', 'current_day': 9545799}
        cohort_user_kwargs = {'finantial_status': 'UP_TO_DATE', 'educational_status': 'GRADUATED'}
        syllabus_kwargs = {'duration_in_days': 9545799}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     capability='crud_certificate',
                                     role='STUDENT',
                                     cohort_user=True,
                                     specialty=True,
                                     syllabus_schedule=True,
                                     user_specialty=True,
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

        url = reverse_lazy('certificate:cohort_id', kwargs={'cohort_id': 1})
        data = {'layout_slug': 'vanilla'}
        start = timezone.now()
        response = self.client.post(url, data, format='json')
        end = timezone.now()
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']

        issued_at = self.iso_to_datetime(json[0]['issued_at'])
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del json[0]['issued_at']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(model.cohort.kickoff_date),
                'ending_date': None,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'schedule': {
                    'id': model['syllabus_schedule'].id,
                    'name': model['syllabus_schedule'].name,
                    'syllabus': model['syllabus_schedule'].syllabus.id,
                },
                'syllabus_version': {
                    'version': model['syllabus_version'].version,
                    'name': model['syllabus_version'].syllabus.name,
                    'slug': model['syllabus_version'].syllabus.slug,
                    'syllabus': model['syllabus_version'].syllabus.id,
                    'duration_in_days': model['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': model['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': model['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'background_url': model['layout_design'].background_url,
                'slug': model['layout_design'].slug
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'description': model['specialty'].description,
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            },
            'profile_academy': {
                'first_name': model['profile_academy'].first_name,
                'id': model['profile_academy'].id,
                'last_name': model['profile_academy'].last_name,
                'status': model['profile_academy'].status,
                'phone': model['profile_academy'].phone,
                'created_at': self.datetime_to_iso(model['profile_academy'].created_at),
                'email': model['profile_academy'].email,
                'academy': {
                    'id': 1,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_specialty = self.bc.database.get('certificate.UserSpecialty', 1, dict=False)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [{
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': model['user_specialty'].preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'PERSISTED',
                'issued_at': issued_at,
                'status_text': 'Certificate successfully queued for PDF generation',
                'user_id': 1,
                'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949',
                'update_hash': user_specialty.update_hash,
            }])

        self.assertEqual(
            signals.user_specialty_saved.send.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Action
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ])
