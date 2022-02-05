"""
Test /cohort/user
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils import DatetimeInteger
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""
    """
    🔽🔽🔽 Auth
    """
    def test_specialty_mode_time_slot__without_auth(self):
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
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
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
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
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
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
                                     role='potato',
                                     specialty_mode=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_specialty_mode_time_slot__with_data(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_certificate',
                                     role='potato',
                                     specialty_mode_time_slot=True)
        model_dict = self.remove_dinamics_fields(model['specialty_mode_time_slot'].__dict__)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.specialty_mode_time_slot.id,
            'academy':
            model.specialty_mode_time_slot.academy.id,
            'specialty_mode':
            model.specialty_mode_time_slot.specialty_mode.id,
            'starting_at':
            self.interger_to_iso(model.specialty_mode_time_slot.timezone,
                                 model.specialty_mode_time_slot.starting_at),
            'ending_at':
            self.interger_to_iso(model.specialty_mode_time_slot.timezone,
                                 model.specialty_mode_time_slot.ending_at),
            'recurrent':
            model.specialty_mode_time_slot.recurrent,
            'recurrency_type':
            model.specialty_mode_time_slot.recurrency_type,
            'created_at':
            self.datetime_to_iso(model.specialty_mode_time_slot.created_at),
            'updated_at':
            self.datetime_to_iso(model.specialty_mode_time_slot.updated_at),
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{
            **self.model_to_dict(model, 'specialty_mode_time_slot'),
        }])

    """
    🔽🔽🔽 Post
    """

    def test_specialty_mode_time_slot__post__without_academy_certificate(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato')
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'certificate-not-found',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__post__without_timezone(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'academy-without-timezone', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__post__without_ending_at_and_starting_at(self):
        self.headers(academy=1)
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True,
                                     academy_kwargs=academy_kwargs)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})
        data = {}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'ending_at': ['This field is required.'],
            'starting_at': ['This field is required.'],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    def test_specialty_mode_time_slot__post(self):
        self.headers(academy=1)
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True,
                                     academy_kwargs=academy_kwargs)
        url = reverse_lazy('admissions:academy_schedule_id_timeslot', kwargs={'certificate_id': 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()
        data = {
            'ending_at': self.datetime_to_iso(ending_at),
            'starting_at': self.datetime_to_iso(starting_at),
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'academy': 1,
            'specialty_mode': 1,
            'id': 1,
            'recurrency_type': 'WEEKLY',
            'recurrent': True,
            'timezone': model.academy.timezone,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_specialty_mode_time_slot_dict(),
            [{
                'academy_id': 1,
                'specialty_mode_id': 1,
                'ending_at': DatetimeInteger.from_datetime(model.academy.timezone, ending_at),
                'id': 1,
                'recurrency_type': 'WEEKLY',
                'recurrent': True,
                'starting_at': DatetimeInteger.from_datetime(model.academy.timezone, starting_at),
                'timezone': model.academy.timezone,
            }],
        )
