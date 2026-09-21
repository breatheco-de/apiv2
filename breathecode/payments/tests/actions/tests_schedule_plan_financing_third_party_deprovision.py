from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

from breathecode.payments import actions
from breathecode.payments.models import PlanFinancing


def _financing(bc, *, status: str, with_vps: bool = False, plan_expires_at=None):
    kwargs = {
        "academy": 1,
        "user": 1,
        "plan": {"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        "plan_financing": {
            "status": status,
            "plan_expires_at": plan_expires_at or (timezone.now() + timedelta(days=30)),
            "valid_until": timezone.now() + timedelta(days=30),
            "next_payment_at": timezone.now() + timedelta(days=30),
            "how_many_installments": 1,
            "installments_paid": 1,
        },
    }
    if with_vps:
        kwargs["service"] = {"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"}
        kwargs["service_item"] = {"how_many": 1}
        kwargs["plan_service_item"] = True
    return bc.database.create(**kwargs)


@pytest.mark.django_db
@patch("breathecode.payments.actions.schedule_task")
def test_skips_when_not_fully_paid(mock_schedule_task, bc):
    model = _financing(bc, status=PlanFinancing.Status.ACTIVE, with_vps=True)
    actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)
    mock_schedule_task.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.payments.actions.schedule_task")
@patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=None)
def test_skips_without_deprovisioner(_mock_get_deprovisioner, mock_schedule_task, bc):
    model = _financing(bc, status=PlanFinancing.Status.FULLY_PAID, with_vps=True)
    actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)
    mock_schedule_task.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.payments.actions.schedule_task")
def test_enqueues_notify_power_off_and_teardown_when_fully_paid(mock_schedule_task, bc):
    from breathecode.payments.tasks import notify_plan_financing_third_party_deprovision
    from breathecode.provisioning.tasks import (
        deprovision_plan_financing_third_party,
        power_off_plan_financing_third_party,
    )

    manager = MagicMock()
    manager.exists.return_value = False
    mock_schedule_task.return_value = manager
    model = _financing(bc, status=PlanFinancing.Status.FULLY_PAID, with_vps=True)

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)

    assert mock_schedule_task.call_count == 3
    assert mock_schedule_task.call_args_list[0].args[0] is notify_plan_financing_third_party_deprovision
    assert mock_schedule_task.call_args_list[1].args[0] is power_off_plan_financing_third_party
    assert mock_schedule_task.call_args_list[2].args[0] is deprovision_plan_financing_third_party
    assert manager.call.call_args_list == [
        call(model.plan_financing.id),
        call(model.plan_financing.id),
        call(model.plan_financing.id),
    ]


@pytest.mark.django_db
@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
@patch("breathecode.payments.actions.schedule_task")
def test_schedules_notify_at_expiry_power_off_at_80_and_teardown_after_grace(mock_schedule_task, bc):
    """FULLY_PAID + VPS: notify at expiry, power-off at 80%, teardown at 100%."""
    from breathecode.payments.tasks import notify_plan_financing_third_party_deprovision
    from breathecode.provisioning.tasks import (
        deprovision_plan_financing_third_party,
        power_off_plan_financing_third_party,
    )

    utc_now = timezone.now()
    plan_expires_at = utc_now + timedelta(days=10)
    manager = MagicMock()
    manager.exists.return_value = False
    mock_schedule_task.return_value = manager
    model = _financing(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        with_vps=True,
        plan_expires_at=plan_expires_at,
    )

    with (
        patch("breathecode.payments.actions.timezone.now", return_value=utc_now),
        patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None),
    ):
        actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)

    assert mock_schedule_task.call_count == 3
    notify_call, power_off_call, teardown_call = mock_schedule_task.call_args_list
    assert notify_call.args[0] is notify_plan_financing_third_party_deprovision
    assert power_off_call.args[0] is power_off_plan_financing_third_party
    assert teardown_call.args[0] is deprovision_plan_financing_third_party
    assert notify_call.args[1] == actions._eta_for_schedule_at(plan_expires_at, utc_now)
    assert power_off_call.args[1] == actions._eta_for_schedule_at(plan_expires_at + timedelta(days=12), utc_now)
    assert teardown_call.args[1] == actions._eta_for_schedule_at(plan_expires_at + timedelta(days=15), utc_now)


@pytest.mark.django_db
@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
@patch("breathecode.payments.actions.schedule_task")
def test_late_window_reanchors_power_off_and_teardown_from_now(mock_schedule_task, bc):
    from breathecode.payments.tasks import notify_plan_financing_third_party_deprovision
    from breathecode.provisioning.tasks import (
        deprovision_plan_financing_third_party,
        power_off_plan_financing_third_party,
    )

    utc_now = timezone.now()
    plan_expires_at = utc_now - timedelta(days=20)
    manager = MagicMock()
    manager.exists.return_value = False
    mock_schedule_task.return_value = manager
    model = _financing(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        with_vps=True,
        plan_expires_at=plan_expires_at,
    )

    with (
        patch("breathecode.payments.actions.timezone.now", return_value=utc_now),
        patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None),
    ):
        actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)

    notify_call, power_off_call, teardown_call = mock_schedule_task.call_args_list
    assert notify_call.args[0] is notify_plan_financing_third_party_deprovision
    assert power_off_call.args[0] is power_off_plan_financing_third_party
    assert teardown_call.args[0] is deprovision_plan_financing_third_party
    assert notify_call.args[1] == actions._eta_for_schedule_at(plan_expires_at, utc_now)
    assert power_off_call.args[1] == actions._eta_for_schedule_at(utc_now + timedelta(days=12), utc_now)
    assert teardown_call.args[1] == actions._eta_for_schedule_at(utc_now + timedelta(days=15), utc_now)
    assert teardown_call.args[1] != actions._eta_for_schedule_at(plan_expires_at + timedelta(days=15), utc_now)


@pytest.mark.django_db
@patch("breathecode.payments.actions.schedule_task")
def test_skips_call_when_teardown_already_done(mock_schedule_task, bc):
    from task_manager.core.actions import parse_payload
    from task_manager.django.models import ScheduledTask

    model = _financing(bc, status=PlanFinancing.Status.FULLY_PAID, with_vps=True)
    ScheduledTask.objects.create(
        task_module="breathecode.provisioning.tasks",
        task_name="deprovision_plan_financing_third_party",
        arguments=parse_payload({"args": [model.plan_financing.id], "kwargs": {}}),
        status="DONE",
        eta=timezone.now(),
        duration=timedelta(),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)

    mock_schedule_task.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.payments.actions.schedule_task")
def test_skips_power_off_when_plan_has_no_power_off_handler(mock_schedule_task, bc):
    from breathecode.payments.tasks import notify_plan_financing_third_party_deprovision
    from breathecode.provisioning.tasks import (
        deprovision_plan_financing_third_party,
        power_off_plan_financing_third_party,
    )

    manager = MagicMock()
    manager.exists.return_value = False
    mock_schedule_task.return_value = manager
    model = bc.database.create(
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
        service={"type": "VOID", "slug": "llm-budget", "consumer": "LLM_BUDGET"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        actions.schedule_plan_financing_third_party_deprovision(model.plan_financing)

    scheduled = [c.args[0] for c in mock_schedule_task.call_args_list]
    assert notify_plan_financing_third_party_deprovision in scheduled
    assert deprovision_plan_financing_third_party in scheduled
    assert power_off_plan_financing_third_party not in scheduled
