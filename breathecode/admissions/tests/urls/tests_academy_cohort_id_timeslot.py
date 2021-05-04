"""
Test /cohort/user
"""
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
    def test_cohort_user__without_auth(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:academy_cohort_id_timeslot', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_user__without_academy_header(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_user_without_capabilities(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_cohort for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without_data
    """
    def test_cohort_user_without_data(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_cohort', role='potato')
        url = reverse_lazy('admissions:academy_cohort_id_timeslot', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_cohort', role='potato', cohort_time_slot=True)
        model_dict = self.remove_dinamics_fields(model['cohort_time_slot'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()
        print(json)
        expected = [{
            'id': 1,
            'cohort': 1,
            'starting_at': None,
            'ending_at': None,
            'starting_hour': '03:10:10',
            'ending_hour': '09:29:55',
            'recurrent': True,
            'recurrency_type':'WEEKLY',
            'created_at': '2021-05-04T13:25:46.709160Z',
            'updated_at': '2021-05-04T13:25:46.709160Z',
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
