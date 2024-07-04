"""
Test /academy/cohort
"""

from unittest.mock import MagicMock, patch, call
from mixer.backend.django import mixer

from ...mixins import AdmissionsTestCase
from ....management.commands.migrate_or_delete_syllabus_schedule import Command


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__without_schedules(self):
        from django.core.management.base import OutputWrapper

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])
        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__without_academy(self):
        """
        Descriptions of models are being generated:

          SyllabusSchedule(id=1):
            academy: Academy(id=1)
        """
        from django.core.management.base import OutputWrapper

        model = self.bc.database.create(syllabus_schedule=1, syllabus_schedule_time_slot=1)
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])
        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Done!"),
            ],
        )

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__without_cohort(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="QJb")

          SyllabusSchedule(id=1):
            academy: Academy(id=1)
        """
        from django.core.management.base import OutputWrapper

        model = self.bc.database.create(syllabus_schedule=1, academy=1, skip_cohort=True, syllabus_schedule_time_slot=1)
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])
        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__without_other_academy__without_timezone(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="UgN")

          Cohort(id=1):
            academy: Academy(id=1)
            schedule: SyllabusSchedule(id=1)

          SyllabusSchedule(id=1):
            academy: Academy(id=1)
        """
        from django.core.management.base import OutputWrapper

        model = self.bc.database.create(syllabus_schedule=1, academy=1, cohort=1, syllabus_schedule_time_slot=1)
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort),
                    "schedule_id": None,
                },
            ],
        )
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__other_academy_without_schedules__without_timezone(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="whs")

          Cohort(id=1):
            academy: Academy(id=1)
            schedule: SyllabusSchedule(id=1)

          Cohort(id=2):
            academy: Academy(id=1)

          SyllabusSchedule(id=1):
            academy: Academy(id=1)
        """
        from django.core.management.base import OutputWrapper

        cohorts = [{"schedule_id": 1}, {"schedule": None}]
        model = self.bc.database.create(syllabus_schedule=1, academy=2, cohort=cohorts, syllabus_schedule_time_slot=1)
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                    "schedule_id": None,
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                    "schedule_id": None,
                },
            ],
        )
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__other_academy_with_two_schedules__inferred_from_cohort(self):
        from django.core.management.base import OutputWrapper

        cohorts = [{"schedule_id": 1, "academy_id": 1}, {"schedule_id": 1, "academy_id": 2}]
        syllabus_schedule = {"academy": None}
        syllabus_schedule_time_slots = (2, {"schedule_id": 1})
        model = self.bc.database.create(
            syllabus_schedule=syllabus_schedule,
            academy=2,
            cohort=cohorts,
            syllabus_schedule_time_slot=syllabus_schedule_time_slots,
        )
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusSchedule"), [])

        self.assertEqual(self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"), [])

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                    "schedule_id": None,
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                    "schedule_id": None,
                },
            ],
        )
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__one_per_academy(self):
        from django.core.management.base import OutputWrapper

        cohorts = [{"schedule_id": 1, "academy_id": 1}, {"schedule_id": 2, "academy_id": 2}]
        syllabus_schedule = {"academy": None}
        academies = [{"timezone": "America/New_York"}, {"timezone": "Pacific/Pago_Pago"}]
        syllabus_schedule_time_slots = [{"schedule_id": 1}, {"schedule_id": 2}]
        model = self.bc.database.create(
            syllabus_schedule=(2, syllabus_schedule),
            academy=academies,
            cohort=cohorts,
            syllabus_schedule_time_slot=syllabus_schedule_time_slots,
        )
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[0]),
                    "academy_id": 1,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[1]),
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "schedule_id": 1,
                    "timezone": "America/New_York",
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "schedule_id": 2,
                    "timezone": "Pacific/Pago_Pago",
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                },
            ],
        )
        self.assertEqual(OutputWrapper.write.call_args_list, [call("Done!")])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__two_schedule_related_to_the_first__two_academy(self):
        from django.core.management.base import OutputWrapper

        cohorts = [
            {"schedule_id": 1, "academy_id": 1},
            {"schedule_id": 2, "academy_id": 1},
            {"schedule_id": 1, "academy_id": 2},
            {"schedule_id": 2, "academy_id": 2},
        ]
        syllabus_schedule = {"academy": None}
        academies = [{"timezone": "America/New_York"}, {"timezone": "Pacific/Pago_Pago"}]
        syllabus_schedule_time_slots = [
            {"schedule_id": 1},
            {"schedule_id": 2},
            {"schedule_id": 3},
            {"schedule_id": 4},
        ]
        model = self.bc.database.create(
            syllabus_schedule=(4, syllabus_schedule),
            academy=academies,
            cohort=cohorts,
            syllabus_schedule_time_slot=syllabus_schedule_time_slots,
        )
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[0]),
                    "academy_id": 1,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[1]),
                    "academy_id": 1,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[0]),
                    "id": 5,
                    "academy_id": 2,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[1]),
                    "id": 6,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "schedule_id": 1,
                    "timezone": model.academy[0].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "schedule_id": 2,
                    "timezone": model.academy[0].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "id": 5,
                    "schedule_id": 5,
                    "timezone": model.academy[1].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "id": 6,
                    "schedule_id": 6,
                    "timezone": model.academy[1].timezone,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                },
                {
                    **self.bc.format.to_dict(model.cohort[2]),
                    "schedule_id": 5,
                },
                {
                    **self.bc.format.to_dict(model.cohort[3]),
                    "schedule_id": 6,
                },
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Done!"),
            ],
        )

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_migrate_or_delete_syllabus_schedule__two_schedule_related_to_the_first__two_academy__cohort_with_timezone(
        self,
    ):
        from django.core.management.base import OutputWrapper

        cohorts = [
            {
                "schedule_id": 1,
                "academy_id": 1,
                "timezone": "Europe/Madrid",
            },
            {
                "schedule_id": 2,
                "academy_id": 1,
                "timezone": "America/Caracas",
            },
            {
                "schedule_id": 1,
                "academy_id": 2,
                "timezone": "America/Bogota",
            },
            {
                "schedule_id": 2,
                "academy_id": 2,
                "timezone": "America/Santiago",
            },
        ]
        syllabus_schedule = {"academy": None}
        academies = [{"timezone": "America/New_York"}, {"timezone": "Pacific/Pago_Pago"}]
        syllabus_schedule_time_slots = [
            {"schedule_id": 1},
            {"schedule_id": 2},
            {"schedule_id": 3},
            {"schedule_id": 4},
        ]
        model = self.bc.database.create(
            syllabus_schedule=(4, syllabus_schedule),
            academy=academies,
            cohort=cohorts,
            syllabus_schedule_time_slot=syllabus_schedule_time_slots,
        )
        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusSchedule"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[0]),
                    "academy_id": 1,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[1]),
                    "academy_id": 1,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[0]),
                    "id": 5,
                    "academy_id": 2,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule[1]),
                    "id": 6,
                    "academy_id": 2,
                },
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("admissions.SyllabusScheduleTimeSlot"),
            [
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "schedule_id": 1,
                    "timezone": model.cohort[0].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "schedule_id": 2,
                    "timezone": model.cohort[1].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[0]),
                    "id": 5,
                    "schedule_id": 5,
                    "timezone": model.cohort[2].timezone,
                },
                {
                    **self.bc.format.to_dict(model.syllabus_schedule_time_slot[1]),
                    "id": 6,
                    "schedule_id": 6,
                    "timezone": model.cohort[3].timezone,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                },
                {
                    **self.bc.format.to_dict(model.cohort[2]),
                    "schedule_id": 5,
                },
                {
                    **self.bc.format.to_dict(model.cohort[3]),
                    "schedule_id": 6,
                },
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Done!"),
            ],
        )
