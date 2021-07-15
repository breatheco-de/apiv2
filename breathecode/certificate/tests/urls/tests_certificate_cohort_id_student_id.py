"""
Test /certificate
"""
import re
from random import choice
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_certificate_test_case import CertificateTestCase

class CertificateTestSuite(CertificateTestCase):
    """Test /certificate/cohort/id/student/id"""
    """
    🔽🔽🔽 Post Method
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_no_default_layout(self):
        """ No main teacher in cohort """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             specialty=True,
                             )

        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_role='TEACHER',
                                             models=base)

        url = reverse_lazy('certificate:certificate_single',
                           kwargs={'cohort_id': 1, 'student_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {
            'detail': 'no-default-layout', 'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_no_cohort_user(self):
        """ No main teacher in cohort """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='POTATO',
                             syllabus=True,
                             specialty=True,
                             )

        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_role='TEACHER',
                                             models=base)

        url = reverse_lazy('certificate:certificate_single',
                           kwargs={'cohort_id': 1, 'student_id': 1})
        response = self.client.post(url, format='json')
        json = response.json()
        expected = {
            'detail': 'student-not-found', 'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_user_specialty_dict(), [])

    
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate(self):
        """ No main teacher in cohort """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                             cohort=True,
                             user=True,
                             profile_academy=True,
                             capability='crud_certificate',
                             role='STUDENT',
                             cohort_user=True,
                             syllabus=True,
                             specialty=True,
                             user_specialty=True,
                             layout_design=True,
                             cohort_user_educational_status='GRADUATED',
                             cohort_user_finantial_status='UP_TO_DATE',
                             cohort_stage="ENDED",
                             cohort_finished=True
                             )
        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_role='TEACHER',
                                             models=base)

        url = reverse_lazy('certificate:certificate_single',
                           kwargs={'cohort_id': 1, 'student_id': 1})
        data = {'layout_slug': 'vanilla'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        self.assertDatetime(json['updated_at'])
        del json['updated_at']
        expected = {
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'syllabus': {
                    'certificate': {
                        'duration_in_hours':
                        model['certificate'].duration_in_hours
                    }
                }
            },
            'created_at':
            self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at':
            model['user_specialty'].expires_at,
            'id':
            1,
            'layout': {
                'name': model['layout_design'].name,
                'background_url': model['layout_design'].background_url,
                'slug': model['layout_design'].slug
            },
            'preview_url':
            model['user_specialty'].preview_url,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            'Director',
            'specialty': {
                'description': None,
                'created_at':
                self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at':
                self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status':
            'PERSISTED',
            'status_text':
            'Certificate successfully queued for PDF generation',
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_user_specialty_dict(), [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + " " +
                        teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text': 'Certificate successfully queued for PDF generation',
            'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949',
            'user_id': 1
            }])
