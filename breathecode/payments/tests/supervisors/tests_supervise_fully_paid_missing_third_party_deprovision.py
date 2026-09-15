from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from task_manager.core.actions import parse_payload
from task_manager.django.models import ScheduledTask

from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue
from breathecode.payments.models import PlanFinancing
from breathecode.payments.supervisors import (
    plan_financing_missing_third_party_deprovision,
    supervise_fully_paid_missing_third_party_deprovision,
)
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


class Supervisor:

    def __init__(self, bc: Breathecode):
        self._bc = bc

    def list(self):
        supervisors = SupervisorModel.objects.all()
        return [
            {
                "task_module": supervisor.task_module,
                "task_name": supervisor.task_name,
            }
            for supervisor in supervisors
        ]

    def log(self, module, name):
        issues = SupervisorIssue.objects.filter(supervisor__task_module=module, supervisor__task_name=name)
        return [x.error for x in issues]


def _fully_paid_with_vps(bc):
    return bc.database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": PlanFinancing.Status.FULLY_PAID,
            "plan_expires_at": timezone.now() + timedelta(days=30),
            "valid_until": timezone.now() + timedelta(days=30),
            "next_payment_at": timezone.now() + timedelta(days=30),
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )


@pytest.mark.django_db
def test_supervise_fully_paid_missing_third_party_deprovision(bc: Breathecode):
    model = _fully_paid_with_vps(bc)

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        supervise_fully_paid_missing_third_party_deprovision()

    supervisor = Supervisor(bc)
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_fully_paid_missing_third_party_deprovision",
        },
    ]
    assert supervisor.log(
        "breathecode.payments.supervisors",
        "supervise_fully_paid_missing_third_party_deprovision",
    ) == [
        f"PlanFinancing {model.plan_financing.id} for user {model.user.email} is FULLY_PAID "
        "but has no third-party deprovision scheduled",
    ]

    issues = list(SupervisorIssue.objects.all())
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "plan-financing-missing-third-party-deprovision"
    assert issue.params == {"plan_financing_id": model.plan_financing.id}

    with patch(
        "breathecode.payments.actions.schedule_plan_financing_third_party_deprovision"
    ) as mock_schedule:
        res = plan_financing_missing_third_party_deprovision(issue.id)
        mock_schedule.assert_called_once()
        assert mock_schedule.call_args.args[0].id == model.plan_financing.id

    assert res is True


@pytest.mark.django_db
def test_supervise_skips_when_teardown_already_done(bc: Breathecode):
    model = _fully_paid_with_vps(bc)
    ScheduledTask.objects.create(
        task_module="breathecode.provisioning.tasks",
        task_name="deprovision_plan_financing_third_party",
        arguments=parse_payload({"args": [model.plan_financing.id], "kwargs": {}}),
        status="DONE",
        eta=timezone.now(),
        duration=timedelta(),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        supervise_fully_paid_missing_third_party_deprovision()

    supervisor = Supervisor(bc)
    assert (
        supervisor.log(
            "breathecode.payments.supervisors",
            "supervise_fully_paid_missing_third_party_deprovision",
        )
        == []
    )


@pytest.mark.django_db
def test_supervise_skips_fully_paid_without_deprovisioner_service(bc: Breathecode):
    bc.database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": PlanFinancing.Status.FULLY_PAID,
            "plan_expires_at": timezone.now() + timedelta(days=30),
            "valid_until": timezone.now() + timedelta(days=30),
            "next_payment_at": timezone.now() + timedelta(days=30),
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        service={"type": "VOID", "slug": "mentorship", "consumer": "NO_SET"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )

    supervise_fully_paid_missing_third_party_deprovision()

    supervisor = Supervisor(bc)
    assert (
        supervisor.log(
            "breathecode.payments.supervisors",
            "supervise_fully_paid_missing_third_party_deprovision",
        )
        == []
    )
