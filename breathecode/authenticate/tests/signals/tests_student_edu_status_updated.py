from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.authenticate.tasks import async_add_to_organization
from breathecode.certificate.tasks import async_generate_certificate
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def patch(db, enable_signals, monkeypatch):
    enable_signals("breathecode.admissions.signals.student_edu_status_updated")
    monkeypatch.setattr("breathecode.certificate.tasks.async_generate_certificate.delay", MagicMock())
    monkeypatch.setattr("breathecode.feedback.tasks.process_student_graduation.delay", MagicMock())
    monkeypatch.setattr("breathecode.marketing.tasks.add_cohort_task_to_student.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.async_add_to_organization.delay", MagicMock())

    yield


ACTIVE = "ACTIVE"
POSTPONED = "POSTPONED"
SUSPENDED = "SUSPENDED"
GRADUATED = "GRADUATED"
DROPPED = "DROPPED"


def all_edutational_statuses_but_active():
    statuses = ["POSTPONED", "SUSPENDED", "GRADUATED", "DROPPED"]

    for old_status in statuses:
        for new_status in statuses:
            if old_status == new_status:
                continue

            yield old_status, new_status


class TestAsyncRemoveFromOrganization:

    def test_the_requirements_are_not_met(self, bc: Breathecode):

        status = "ACTIVE"
        bc.database.create(cohort_user={"educational_status": status})

        assert bc.database.list_of("task_manager.ScheduledTask") == []
        assert async_add_to_organization.delay.call_args_list == [call(1, 1)]

    @pytest.mark.parametrize("status", ["POSTPONED", "SUSPENDED", "GRADUATED", "DROPPED"])
    def test_the_requirements_are_met(self, bc: Breathecode, status, set_datetime):

        delta = timedelta(days=21)
        now = timezone.now()
        set_datetime(now)

        bc.database.create(cohort_user={"educational_status": status})

        assert bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "arguments": {
                    "args": [
                        1,
                        1,
                    ],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": now + delta,
                "id": 1,
                "status": "PENDING",
                "task_module": "breathecode.authenticate.tasks",
                "task_name": "async_remove_from_organization",
            },
        ]
        assert async_add_to_organization.delay.call_args_list == []

    @pytest.mark.parametrize("old_status, new_status", [*all_edutational_statuses_but_active()])
    def test_the_requirements_are_met__it_is_not_triggered_twice(
        self, bc: Breathecode, set_datetime, old_status, new_status
    ):

        delta = timedelta(days=21)
        now = timezone.now()
        set_datetime(now)

        model = bc.database.create(cohort_user=(2, {"educational_status": old_status}))

        for x in model.cohort_user:
            x.educational_status = new_status
            x.save()

        assert bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "arguments": {
                    "args": [
                        1,
                        1,
                    ],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": now + delta,
                "id": 1,
                "status": "PENDING",
                "task_module": "breathecode.authenticate.tasks",
                "task_name": "async_remove_from_organization",
            },
        ]
        assert async_add_to_organization.delay.call_args_list == []


class TestGenerateCertificate:

    @pytest.mark.parametrize(
        "available_as_saas, educational_status",
        [
            (False, "GRADUATED"),
            (True, "ACTIVE"),
            (True, "POSTPONED"),
            (True, "SUSPENDED"),
            (True, "DROPPED"),
        ],
    )
    def test_the_requirements_are_not_met(self, bc: Breathecode, available_as_saas, educational_status):
        bc.database.create(
            cohort_user={"educational_status": educational_status}, cohort={"available_as_saas": available_as_saas}
        )

        assert async_generate_certificate.delay.call_args_list == []

    def test_the_requirements_met(self, bc: Breathecode):
        bc.database.create(cohort_user={"educational_status": "GRADUATED"}, cohort={"available_as_saas": True})

        assert async_generate_certificate.delay.call_args_list == [call(1, 1)]
