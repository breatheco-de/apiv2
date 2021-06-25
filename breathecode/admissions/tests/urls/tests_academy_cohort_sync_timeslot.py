"""
Test /certificate
"""
from unittest.mock import patch
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    """
    🔽🔽🔽 Auth
    """
    def test_academy_cohort_sync_timeslot__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:academy_cohort_sync_timeslot')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_sync_timeslot')
        self.generate_models(authenticate=True)

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code':
            403,
            'detail':
            'You (user: 1) don\'t have this capability: crud_certificate '
            'for academy 1'
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without cohort in the querystring
    """

    def test_academy_cohort_sync_timeslot__without_cohort_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_sync_timeslot')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'missing-cohort-in-querystring',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__with_cohort_in_querystring__without_certificate(
            self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'cohort-without-certificate',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__with_cohort_in_querystring__with_certificate(
            self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     certificate=True,
                                     syllabus=True)

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without cohort timeslot
    """

    def test_academy_cohort_sync_timeslot__with_one_certificate_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     certificate=True,
                                     syllabus=True,
                                     certificate_time_slot=True)

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [{
            'id':
            1,
            'cohort':
            model.cohort.id,
            'starting_at':
            self.datetime_to_iso(model.certificate_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(model.certificate_time_slot.ending_at),
            'recurrent':
            model.certificate_time_slot.recurrent,
            'recurrency_type':
            model.certificate_time_slot.recurrency_type,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [{
                'id': 1,
                'cohort_id': model.cohort.id,
                'starting_at': model.certificate_time_slot.starting_at,
                'ending_at': model.certificate_time_slot.ending_at,
                'recurrent': model.certificate_time_slot.recurrent,
                'recurrency_type': model.certificate_time_slot.recurrency_type,
            }])

    def test_academy_cohort_sync_timeslot__with_two_certificate_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1'
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_certificate',
                                    role='potato',
                                    certificate=True,
                                    syllabus=True)

        models = [
            self.generate_models(certificate_time_slot=True, models=base)
            for _ in range(0, 2)
        ]

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [{
            'id':
            model.certificate_time_slot.id,
            'cohort':
            model.cohort.id,
            'starting_at':
            self.datetime_to_iso(model.certificate_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(model.certificate_time_slot.ending_at),
            'recurrent':
            model.certificate_time_slot.recurrent,
            'recurrency_type':
            model.certificate_time_slot.recurrency_type,
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [{
                'id': model.certificate_time_slot.id,
                'cohort_id': model.cohort.id,
                'starting_at': model.certificate_time_slot.starting_at,
                'ending_at': model.certificate_time_slot.ending_at,
                'recurrent': model.certificate_time_slot.recurrent,
                'recurrency_type': model.certificate_time_slot.recurrency_type,
            } for model in models])

    """
    🔽🔽🔽 With two cohorts
    """

    def test_academy_cohort_sync_timeslot__with_two_certificate_timeslot__with_two_cohort(
            self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1,2'
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_certificate',
                                    role='potato',
                                    certificate=True,
                                    syllabus=True,
                                    skip_cohort=True)

        cohorts = [
            self.generate_models(cohort=True, models=base).cohort
            for _ in range(0, 2)
        ]

        certificate_timeslots = [
            self.generate_models(certificate_time_slot=True,
                                 models=base).certificate_time_slot
            for _ in range(0, 2)
        ]

        data = {}
        response = self.client.post(url, data)
        json = response.json()

        # base = 0
        expected = [{
            'id':
            certificate_time_slot.id,
            'cohort':
            1,
            'starting_at':
            self.datetime_to_iso(certificate_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(certificate_time_slot.ending_at),
            'recurrent':
            certificate_time_slot.recurrent,
            'recurrency_type':
            certificate_time_slot.recurrency_type,
        } for certificate_time_slot in certificate_timeslots] + [{
            'id':
            certificate_time_slot.id + 2,
            'cohort':
            2,
            'starting_at':
            self.datetime_to_iso(certificate_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(certificate_time_slot.ending_at),
            'recurrent':
            certificate_time_slot.recurrent,
            'recurrency_type':
            certificate_time_slot.recurrency_type,
        } for certificate_time_slot in certificate_timeslots]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [{
                'id': certificate_time_slot.id,
                'cohort_id': 1,
                'starting_at': certificate_time_slot.starting_at,
                'ending_at': certificate_time_slot.ending_at,
                'recurrent': certificate_time_slot.recurrent,
                'recurrency_type': certificate_time_slot.recurrency_type,
            } for certificate_time_slot in certificate_timeslots] +
            [{
                'id': certificate_time_slot.id + 2,
                'cohort_id': 2,
                'starting_at': certificate_time_slot.starting_at,
                'ending_at': certificate_time_slot.ending_at,
                'recurrent': certificate_time_slot.recurrent,
                'recurrency_type': certificate_time_slot.recurrency_type,
            } for certificate_time_slot in certificate_timeslots])

    """
    🔽🔽🔽 With cohort timeslot
    """

    def test_academy_cohort_sync_timeslot__with_one_cohort_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            'admissions:academy_cohort_sync_timeslot') + '?cohort=1'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     certificate=True,
                                     syllabus=True,
                                     cohort_time_slot=True,
                                     certificate_time_slot=True)

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [{
            'id':
            2,
            'cohort':
            model.cohort.id,
            'starting_at':
            self.datetime_to_iso(model.certificate_time_slot.starting_at),
            'ending_at':
            self.datetime_to_iso(model.certificate_time_slot.ending_at),
            'recurrent':
            model.certificate_time_slot.recurrent,
            'recurrency_type':
            model.certificate_time_slot.recurrency_type,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [{
                'id': 2,
                'cohort_id': model.cohort.id,
                'starting_at': model.certificate_time_slot.starting_at,
                'ending_at': model.certificate_time_slot.ending_at,
                'recurrent': model.certificate_time_slot.recurrent,
                'recurrency_type': model.certificate_time_slot.recurrency_type,
            }])
