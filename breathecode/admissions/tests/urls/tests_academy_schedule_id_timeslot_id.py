"""
Test /cohort/user
"""
import pytz
from datetime import datetime, date, time
from django.urls.base import reverse_lazy
from django.utils import timezone
from dateutil.tz import gettz
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""
    """
    🔽🔽🔽 Auth
    """
    def test_specialty_mode_time_slot__without_auth(self):
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_specialty_mode_time_slot__without_academy_header(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_certificate for academy 1",
                'status_code': 403,
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_specialty_mode_time_slot__without_data(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'time-slot-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_specialty_mode_time_slot__with_data(self):
        self.headers(academy=1)

        date = 202310301330
        iso_string = datetime(2023, 10, 30, 13, 30, tzinfo=gettz('Europe/Amsterdam')).astimezone(
            pytz.UTC).isoformat()[:-6] + 'Z'

        specialty_mode_time_slot_kwargs = {
            'starting_at': date,
            'ending_at': date,
            'timezone': 'Europe/Amsterdam',
        }

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     specialty_mode_time_slot=True,
                                     specialty_mode_time_slot_kwargs=specialty_mode_time_slot_kwargs)

        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model.specialty_mode_time_slot.id,
            'academy': model.specialty_mode_time_slot.academy.id,
            'specialty_mode': model.specialty_mode_time_slot.specialty_mode.id,
            'starting_at': iso_string,
            'ending_at': iso_string,
            'recurrent': model.specialty_mode_time_slot.recurrent,
            'recurrency_type': model.specialty_mode_time_slot.recurrency_type,
            'created_at': self.datetime_to_iso(model.specialty_mode_time_slot.created_at),
            'updated_at': self.datetime_to_iso(model.specialty_mode_time_slot.updated_at),
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{
            **self.model_to_dict(model, 'specialty_mode_time_slot'),
        }])
        # assert False

    """
    🔽🔽🔽 Put
    """

    def test_specialty_mode_time_slot__put__without_academy_certificate(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'certificate-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__put__without_time_slot(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'time-slot-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__put__without_timezone(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'academy-without-timezone', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{
            **self.model_to_dict(model, 'specialty_mode_time_slot'),
        }])

    def test_specialty_mode_time_slot__put__without_ending_at_and_starting_at(self):
        self.headers(academy=1)
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True,
                                     academy_kwargs=academy_kwargs)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        data = {}
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'ending_at': ['This field is required.'],
            'starting_at': ['This field is required.'],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{
            **self.model_to_dict(model, 'specialty_mode_time_slot'),
        }])

    def test_specialty_mode_time_slot__put(self):
        self.headers(academy=1)
        academy_kwargs = {'timezone': 'Europe/Amsterdam'}

        date = 202310301330
        iso_string = datetime(2023, 10, 30, 13, 30, tzinfo=gettz('Europe/Amsterdam')).astimezone(
            pytz.UTC).isoformat()[:-6] + 'Z'

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode_time_slot=True,
                                     specialty_mode=True,
                                     academy_kwargs=academy_kwargs)

        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })

        data = {
            'ending_at': iso_string,
            'starting_at': iso_string,
        }

        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'academy': 1,
            'specialty_mode': 1,
            'id': 1,
            'recurrency_type': 'WEEKLY',
            'recurrent': True,
            'timezone': model.academy.timezone
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(),
                         [{
                             **self.model_to_dict(model, 'specialty_mode_time_slot'),
                             'ending_at': date,
                             'starting_at': date,
                             'timezone': model.academy.timezone,
                         }])

    """
    🔽🔽🔽 Delete
    """

    def test_specialty_mode_time_slot__delete__without_time_slot(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'time-slot-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__delete(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     specialty_mode_time_slot=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot_id',
                           kwargs={
                               'certificate_id': 1,
                               'timeslot_id': 1
                           })
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])
