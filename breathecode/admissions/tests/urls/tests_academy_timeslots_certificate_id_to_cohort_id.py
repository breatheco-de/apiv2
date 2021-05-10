"""
Test /cohort/user
"""
from breathecode.admissions.models import CohortTimeSlot
from datetime import time
from random import choice
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase

class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 Auth
    """
    def test_certificate_time_slot__without_auth(self):
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_certificate_time_slot__without_academy_header(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_certificate_time_slot__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Post
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_time_slot__post__without_academy_certificate(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_certificate', role='potato')
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'certificate-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_time_slot__post__with_bad_cohort_id(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_certificate', role='potato', academy_certificate=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 999})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'cohort-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_time_slot__post__without_certificate_time_slot(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_certificate', role='potato', academy_certificate=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'certificate-time-slots-not-exists', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_time_slot__post(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_certificate', role='potato', academy_certificate=True,
            certificate_time_slot=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'id': 1,
            'cohort': 1,
            'starting_at': self.datetime_to_iso(model.certificate_time_slot.starting_at),
            'ending_at': self.datetime_to_iso(model.certificate_time_slot.ending_at),
            'recurrent': model.certificate_time_slot.recurrent,
            'recurrency_type': model.certificate_time_slot.recurrency_type,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_time_slot = {
            **self.model_to_dict(model, 'certificate_time_slot'),
            'id': 1,
            'cohort_id': 1
        }

        del cohort_time_slot['academy_id']
        del cohort_time_slot['certificate_id']

        self.assertEqual(self.all_cohort_time_slot_dict(), [cohort_time_slot])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_time_slot__post__one_cohort_with_time_slots(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_certificate', role='potato', academy_certificate=True,
            certificate_time_slot=True, cohort_time_slot=True)
        url = reverse_lazy('admissions:academy_timeslots_certificate_id_to_cohort_id', kwargs={'certificate_id': 1, 'cohort_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'certificate-time-slots-is-already-imported',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            **self.model_to_dict(model, 'cohort_time_slot'),
        }])
