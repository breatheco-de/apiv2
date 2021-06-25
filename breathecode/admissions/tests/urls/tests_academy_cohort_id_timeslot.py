"""
Test /cohort/user
"""
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
    def test_cohort_time_slot__without_auth(self):
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_time_slot__without_academy_header(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_time_slot__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: read_cohort for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_cohort_time_slot__without_data(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_time_slot__with_data(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     cohort_time_slot=True)
        model_dict = self.remove_dinamics_fields(
            model['cohort_time_slot'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort_time_slot.id,
            'cohort':
            model.cohort_time_slot.cohort.id,
            'starting_at':
            self.datetime_to_iso(model.cohort_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(model.cohort_time_slot.ending_at),
            'recurrent':
            model.cohort_time_slot.recurrent,
            'recurrency_type':
            model.cohort_time_slot.recurrency_type,
            'created_at':
            self.datetime_to_iso(model.cohort_time_slot.created_at),
            'updated_at':
            self.datetime_to_iso(model.cohort_time_slot.updated_at),
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            **self.model_to_dict(model, 'cohort_time_slot'),
        }])

    """
    🔽🔽🔽 Post
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_time_slot__post__without_ending_at_and_starting_at(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'ending_at': ['This field is required.'],
            'starting_at': ['This field is required.'],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_time_slot__post(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_id_timeslot',
                           kwargs={'cohort_id': 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()
        data = {
            'ending_at': self.datetime_to_iso(ending_at),
            'starting_at': self.datetime_to_iso(starting_at),
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'cohort': 1,
            'ending_at': None,
            'id': 1,
            'recurrency_type': 'WEEKLY',
            'recurrent': True,
            'starting_at': None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_time_slot_dict(),
                         [{
                             'cohort_id': 1,
                             'ending_at': ending_at,
                             'id': 1,
                             'recurrency_type': 'WEEKLY',
                             'recurrent': True,
                             'starting_at': starting_at,
                         }])
