"""
Test /cohort/user
"""
from unittest.mock import patch
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.admissions.models import SpecialtyModeTimeSlot
from breathecode.admissions.admin import replicate_in_all
from ..mixins import AdmissionsTestCase
from django.http.request import HttpRequest


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""
    """
    🔽🔽🔽 With zero Academy
    """
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all(self):
        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 With one Academy and zero SpecialtyMode
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all__with_zero_specialty_modes(self):
        self.generate_models(academy=True)

        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.all()

        replicate_in_all(None, request, queryset)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 With one Academy and one SpecialtyMode
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all__with_one_specialty_mode(self):
        self.generate_models(academy=True, specialty_mode=True)

        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.all()

        replicate_in_all(None, request, queryset)
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [])

    """
    🔽🔽🔽 With one Academy and one SpecialtyMode
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all__with_one_specialty_mode_type_slot(self):
        model = self.generate_models(academy=True, specialty_mode=True, specialty_mode_time_slot=True)

        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.all()

        replicate_in_all(None, request, queryset)

        data = self.model_to_dict(model, 'specialty_mode_time_slot')
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{**data, 'id': 2}])

    """
    🔽🔽🔽 With one Academy, one SpecialtyMode and two Academy
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all__with_one_specialty_mode_type_slot__with_two_academies(self):
        model1 = self.generate_models(academy=True, specialty_mode=True, specialty_mode_time_slot=True)
        model2 = self.generate_models(academy=True)

        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.filter(id=1)

        replicate_in_all(None, request, queryset)

        data = self.model_to_dict(model1, 'specialty_mode_time_slot')
        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [{
            **data,
            'id': 2,
        }, {
            **data,
            'id': 3,
            'academy_id': model2.academy.id,
        }])

    """
    🔽🔽🔽 Select many timeslots from diferent academies
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_replicate_in_all__with_many_timeslots_from_diferent_academies(self):
        academy_model1 = self.generate_models(academy=True)
        academy_model2 = self.generate_models(academy=True)
        models = [
            self.generate_models(
                academy=academy_model1.academy, specialty_mode=True, specialty_mode_time_slot=True)
            for _ in range(1, 3)
        ] + [
            self.generate_models(
                academy=academy_model2.academy, specialty_mode=True, specialty_mode_time_slot=True)
            for _ in range(1, 4)
        ]

        request = HttpRequest()
        queryset = SpecialtyModeTimeSlot.objects.filter().exclude(id=1).exclude(id=3)

        replicate_in_all(None, request, queryset)

        data1 = self.model_to_dict(models[0], 'specialty_mode_time_slot')
        data2 = self.model_to_dict(models[1], 'specialty_mode_time_slot')
        data3 = self.model_to_dict(models[2], 'specialty_mode_time_slot')
        data4 = self.model_to_dict(models[3], 'specialty_mode_time_slot')
        data5 = self.model_to_dict(models[4], 'specialty_mode_time_slot')

        self.assertEqual(self.all_specialty_mode_time_slot_dict(), [
            data1,
            data3,
            {
                **data2,
                'id': 6,
                'academy_id': academy_model1.academy.id,
            },
            {
                **data4,
                'id': 7,
                'academy_id': academy_model1.academy.id,
            },
            {
                **data5,
                'id': 8,
                'academy_id': academy_model1.academy.id,
            },
            {
                **data2,
                'id': 9,
                'academy_id': academy_model2.academy.id,
            },
            {
                **data4,
                'id': 10,
                'academy_id': academy_model2.academy.id,
            },
            {
                **data5,
                'id': 11,
                'academy_id': academy_model2.academy.id,
            },
        ])
