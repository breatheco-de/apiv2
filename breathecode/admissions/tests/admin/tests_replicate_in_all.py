"""
Test replicate_in_all
"""

from unittest.mock import MagicMock, call, patch
from breathecode.admissions.models import SyllabusSchedule
from breathecode.admissions.admin import replicate_in_all
from ..mixins import AdmissionsTestCase
from django.http.request import HttpRequest


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 With zero Academy
    """

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_zero_schedules(self):
        from django.contrib import messages

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])
        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])
        self.assertEqual(
            messages.add_message.call_args_list,
            [call(request, 20, "All academies in sync with those syllabus schedules")],
        )

    """
    🔽🔽🔽 With one Academy and one SyllabusSchedule
    """

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__just_the_same_academy(self):
        from django.contrib import messages

        model = self.bc.database.create(academy=1, syllabus_schedule=1)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                self.bc.format.to_dict(model.syllabus_schedule),
            ],
        )

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            messages.add_message.call_args_list,
            [call(request, 20, "All academies in sync with those syllabus schedules")],
        )

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__two_academies__without_timezone(self):
        from django.contrib import messages

        model = self.bc.database.create(academy=2, syllabus_schedule=1)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                self.bc.format.to_dict(model.syllabus_schedule),
            ],
        )

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            messages.add_message.call_args_list,
            [
                call(
                    request,
                    40,
                    f"The following academies ({model.academy[1].slug}) was skipped "
                    "because it doesn't have a timezone assigned",
                )
            ],
        )

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__two_academies(self):
        from django.contrib import messages

        academy = {"timezone": "Pacific/Pago_Pago"}
        model = self.bc.database.create(academy=(2, academy), syllabus_schedule=1)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule)},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule),
                    "id": 2,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            messages.add_message.call_args_list,
            [
                call(request, 20, "All academies in sync with those syllabus schedules"),
            ],
        )

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__two_academies__zero_timeslots(self):
        from django.contrib import messages

        academy = {"timezone": "Pacific/Pago_Pago"}
        model = self.bc.database.create(academy=(2, academy), syllabus_schedule=1)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule)},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule),
                    "id": 2,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            messages.add_message.call_args_list,
            [
                call(request, 20, "All academies in sync with those syllabus schedules"),
            ],
        )

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__two_academies__one_timeslot(self):
        from django.contrib import messages

        academy = {"timezone": "Pacific/Pago_Pago"}
        model = self.bc.database.create(academy=(2, academy), syllabus_schedule=1, syllabus_schedule_time_slot=1)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule)},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule),
                    "id": 2,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule_time_slot)},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot),
                    "id": 2,
                    "schedule_id": 2,
                    "timezone": model.academy[1].timezone,
                },
            ],
        )

        self.assertEqual(
            messages.add_message.call_args_list,
            [
                call(request, 20, "All academies in sync with those syllabus schedules"),
            ],
        )

    @patch("django.contrib.messages.add_message", MagicMock())
    def test_replicate_in_all__with_one_schedule__two_academies__two_timeslots(self):
        from django.contrib import messages

        academy = {"timezone": "Pacific/Pago_Pago"}
        model = self.bc.database.create(academy=(2, academy), syllabus_schedule=1, syllabus_schedule_time_slot=2)

        request = HttpRequest()
        queryset = SyllabusSchedule.objects.all()

        replicate_in_all(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule)},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule),
                    "id": 2,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"),
            [
                {**self.bc.format.to_dict(model.syllabus_schedule_time_slot[0])},
                {**self.bc.format.to_dict(model.syllabus_schedule_time_slot[1])},
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "id": 3,
                    "schedule_id": 2,
                    "timezone": model.academy[1].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "id": 4,
                    "schedule_id": 2,
                    "timezone": model.academy[1].timezone,
                },
            ],
        )

        self.assertEqual(
            messages.add_message.call_args_list,
            [
                call(request, 20, "All academies in sync with those syllabus schedules"),
            ],
        )
